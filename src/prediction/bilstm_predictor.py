"""
Bi-LSTM trajectory predictor — détection de spoofing par cohérence de trajectoire.

Workflow :
    1. Entraînement sur la trajectoire PROPRE (originale) avec train_ratio.
    2. Calibration automatique des seuils sur les résidus d'entraînement
       (mean + k * sigma) → ~0 faux positifs sur données propres.
    3. Prédiction en batch (rapide) sur la trajectoire à tester (éventuellement spoofée).
    4. Détection de l'onset par fenêtre glissante de points consécutifs suspects.

Usage :
    from src.prediction.bilstm_predictor import BiLSTMPredictor

    predictor = BiLSTMPredictor(epochs=30, threshold_sigma=4.0)
    df_clean   = predictor.trajectory_to_dataframe(clean_trajectory)
    df_spoofed = predictor.trajectory_to_dataframe(spoofed_trajectory)
    predictor.train(df_clean)
    results = predictor.predict(df_spoofed)
    print("Onset à l'index :", results['onset_index'])
"""

from typing import Any
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]


class BiLSTMPredictor:
    """
    Prédicteur Bi-LSTM pour la détection de spoofing GPS/ADS-B.

    Architecture :
        Bidirectional LSTM(128, return_seq=True) → Dropout(0.2)
        → Bidirectional LSTM(64) → Dropout(0.2) → Dense(32) → Dense(3)

    Seuils adaptatifs calibrés automatiquement après l'entraînement :
        threshold = mean(résidu_train) + sigma * std(résidu_train)
    """

    def __init__(
        self,
        window_size:           int   = 50,
        epochs:                int   = 30,
        batch_size:            int   = 32,
        train_ratio:           float = 0.75,
        threshold_sigma:       float = 4.0,
        onset_min_consecutive: int   = 3,
    ):
        """
        Parameters
        ----------
        window_size           : Points passés utilisés pour prédire le suivant.
        epochs                : Epochs d'entraînement.
        batch_size            : Taille des batchs Keras.
        train_ratio           : Fraction de la trajectoire propre utilisée pour
                                l'entraînement (le reste sert à la calibration).
        threshold_sigma       : k dans threshold = mean + k * std des résidus.
                                Valeur haute (4–5) → moins de faux positifs.
        onset_min_consecutive : Nombre minimum de points suspects consécutifs
                                avant de déclarer un onset.
        """
        self.window_size           = window_size
        self.epochs                = epochs
        self.batch_size            = batch_size
        self.train_ratio           = train_ratio
        self.threshold_sigma       = threshold_sigma
        self.onset_min_consecutive = onset_min_consecutive

        self.model: Any       = None
        self.scaler_X         = StandardScaler()
        self.scaler_y         = StandardScaler()
        self._trained         = False
        self.training_history = None

        # Seuils calibrés (mis à jour après train())
        self.lat_threshold: float = 0.1
        self.lon_threshold: float = 0.1
        self.alt_threshold: float = 300.0

    # ------------------------------------------------------------------
    # Conversion Trajectory → DataFrame
    # ------------------------------------------------------------------

    def trajectory_to_dataframe(self, trajectory) -> pd.DataFrame:
        """
        Convertit un objet Trajectory en DataFrame compatible avec le Bi-LSTM.
        Colonnes : time, lat, lon, altitude, speed (m/s), heading (°).
        """
        positions  = trajectory.positions
        timestamps = trajectory.get_timestamps()

        lats = np.array([p.latitude  for p in positions])
        lons = np.array([p.longitude for p in positions])
        alts = np.array([p.altitude  for p in positions])

        try:
            coords_cart = trajectory.get_cartesian_array()
            dt  = np.diff(timestamps)
            dt  = np.where(dt <= 0, 1.0, dt)
            dx  = np.diff(coords_cart[:, 0])
            dy  = np.diff(coords_cart[:, 1])
            speed = np.sqrt(dx ** 2 + dy ** 2) / dt
            speed = np.concatenate([[speed[0]], speed])
        except Exception:
            speed = np.zeros(len(positions))

        dlat    = np.diff(lats)
        dlon    = np.diff(lons)
        heading = np.degrees(np.arctan2(dlon, dlat)) % 360
        heading = np.concatenate([[heading[0]], heading])

        return pd.DataFrame({
            'time':     timestamps,
            'lat':      lats,
            'lon':      lons,
            'altitude': alts,
            'speed':    speed,
            'heading':  heading,
        })

    # ------------------------------------------------------------------
    # Construction des séquences
    # ------------------------------------------------------------------

    def _build_sequences(self, X: np.ndarray, y: np.ndarray):
        """Fenêtres glissantes pour l'entraînement."""
        X_seq, y_seq = [], []
        for i in range(self.window_size, len(X)):
            X_seq.append(X[i - self.window_size:i])
            y_seq.append(y[i])
        return np.array(X_seq), np.array(y_seq)

    def _build_X_sequences(self, X: np.ndarray) -> np.ndarray:
        """Fenêtres glissantes pour la prédiction batch (sans cible)."""
        return np.array([X[i - self.window_size:i]
                         for i in range(self.window_size, len(X))])

    # ------------------------------------------------------------------
    # Entraînement
    # ------------------------------------------------------------------

    def train(self, df_clean: pd.DataFrame, verbose: int = 0, callbacks=None):
        """
        Entraîne le Bi-LSTM sur les `train_ratio` premiers points de df_clean
        (trajectoire propre sans spoofing) et calibre les seuils adaptatifs.

        Parameters
        ----------
        df_clean  : DataFrame issu de trajectory_to_dataframe() sur la trajectoire PROPRE.
        verbose   : Verbosité Keras (0 = silencieux).
        callbacks : Callbacks Keras optionnels (ex: LambdaCallback pour Streamlit).

        Returns
        -------
        history : History Keras.
        """
        try:
            from keras.models import Sequential  # type: ignore[import-untyped]
            from keras.layers import LSTM, Dense, Bidirectional, Dropout  # type: ignore[import-untyped]
            from keras.optimizers import Adam  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "TensorFlow/Keras est requis pour le Bi-LSTM.\n"
                "Installez-le avec : pip install tensorflow"
            ) from e

        n       = len(df_clean)
        n_train = max(self.window_size + 10, int(n * self.train_ratio))
        df_tr   = df_clean.iloc[:n_train]

        if len(df_tr) < self.window_size + 2:
            raise ValueError(
                f"Données d'entraînement trop courtes : {len(df_tr)} points "
                f"(minimum {self.window_size + 2} requis)."
            )

        features = ["lat", "lon", "altitude", "speed", "heading"]
        target   = ["lat", "lon", "altitude"]

        X_tr = self.scaler_X.fit_transform(df_tr[features].values)
        y_tr = self.scaler_y.fit_transform(df_tr[target].values)

        X_seq, y_seq = self._build_sequences(X_tr, y_tr)

        # Architecture améliorée : 2 couches Bi-LSTM empilées + Dropout
        self.model = Sequential([
            Bidirectional(
                LSTM(128, return_sequences=True),
                input_shape=(self.window_size, len(features))
            ),
            Dropout(0.2),
            Bidirectional(LSTM(64, return_sequences=False)),
            Dropout(0.2),
            Dense(32, activation="relu"),
            Dense(len(target)),
        ])
        self.model.compile(optimizer=Adam(learning_rate=0.001), loss="mse")

        self.training_history = self.model.fit(
            X_seq,
            y_seq,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.1,
            verbose=verbose,
            callbacks=callbacks or [],
        )

        # ---- Calibration adaptive des seuils sur résidus d'entraînement ----
        # Utilise la partie restante (calibration set) si disponible,
        # sinon les résidus d'entraînement.
        n_calib_start = n_train
        if n_calib_start + self.window_size + 2 < n:
            # Calibration sur données tenues en réserve
            X_full   = self.scaler_X.transform(df_clean[features].values)
            y_full   = df_clean[target].values
            X_c_seq  = self._build_X_sequences(X_full[n_calib_start - self.window_size:])
            y_c_real = y_full[n_calib_start:][:len(X_c_seq)]
        else:
            # Fallback : calibration sur résidus d'entraînement
            tr_pred_sc = self.model.predict(X_seq, verbose=0)
            X_c_seq    = None
            y_c_real   = self.scaler_y.inverse_transform(y_seq)
            _pred      = self.scaler_y.inverse_transform(tr_pred_sc)
            errs_lat   = np.abs(y_c_real[:, 0] - _pred[:, 0])
            errs_lon   = np.abs(y_c_real[:, 1] - _pred[:, 1])
            errs_alt   = np.abs(y_c_real[:, 2] - _pred[:, 2])
            self._set_thresholds(errs_lat, errs_lon, errs_alt)
            self._trained = True
            return self.training_history

        if X_c_seq is not None and len(X_c_seq) > 0:
            c_pred_sc = self.model.predict(X_c_seq, verbose=0)
            c_pred    = self.scaler_y.inverse_transform(c_pred_sc)
            errs_lat  = np.abs(y_c_real[:, 0] - c_pred[:, 0])
            errs_lon  = np.abs(y_c_real[:, 1] - c_pred[:, 1])
            errs_alt  = np.abs(y_c_real[:, 2] - c_pred[:, 2])
            self._set_thresholds(errs_lat, errs_lon, errs_alt)

        self._trained = True
        return self.training_history

    def _set_thresholds(self, errs_lat, errs_lon, errs_alt):
        """Définit les seuils adaptatifs (mean + k*std)."""
        k = self.threshold_sigma
        self.lat_threshold = float(np.mean(errs_lat) + k * np.std(errs_lat))
        self.lon_threshold = float(np.mean(errs_lon) + k * np.std(errs_lon))
        self.alt_threshold = float(np.mean(errs_alt) + k * np.std(errs_alt))

    # ------------------------------------------------------------------
    # Prédiction / Détection
    # ------------------------------------------------------------------

    def predict(self, df: pd.DataFrame) -> dict:
        """
        Prédiction batch sur `df` (trajectoire à tester, éventuellement spoofée)
        et détection du spoofing.

        Returns
        -------
        dict avec :
            predicted             : (N, 3) positions prédites [lat, lon, alt]
            real                  : (N, 3) positions reçues
            spoof_flags           : (N,) booléens — True = suspect
            lat_errs, lon_errs, alt_errs : (N,) erreurs
            indices               : indices originaux dans df (offset = window_size)
            n_spoofed             : nb de points suspects
            n_total               : nb de points analysés
            risk_score            : fraction de points suspects (0–1)
            onset_index           : premier index original de l'onset (ou None)
            onset_detected        : True si spoofing détecté
            lat_threshold         : seuil adaptatif calibré
            lon_threshold         : seuil adaptatif calibré
            alt_threshold         : seuil adaptatif calibré
        """
        if not self._trained or self.model is None:
            raise RuntimeError("Le modèle doit être entraîné avant la prédiction.")

        features = ["lat", "lon", "altitude", "speed", "heading"]
        target   = ["lat", "lon", "altitude"]

        X_scaled  = self.scaler_X.transform(df[features].values)
        y_raw     = df[target].values

        # Prédiction batch (beaucoup plus rapide que point-à-point)
        X_seq     = self._build_X_sequences(X_scaled)
        pred_sc   = self.model.predict(X_seq, batch_size=self.batch_size, verbose=0)
        predicted = self.scaler_y.inverse_transform(pred_sc)

        real    = y_raw[self.window_size:]
        indices = list(range(self.window_size, len(df)))

        lat_errs = np.abs(real[:, 0] - predicted[:, 0])
        lon_errs = np.abs(real[:, 1] - predicted[:, 1])
        alt_errs = np.abs(real[:, 2] - predicted[:, 2])

        spoof_flags = (
            (lat_errs > self.lat_threshold) |
            (lon_errs > self.lon_threshold) |
            (alt_errs > self.alt_threshold)
        )

        onset_index = self._find_onset(spoof_flags, indices)

        return {
            'predicted':      predicted,
            'real':           real,
            'spoof_flags':    spoof_flags,
            'lat_errs':       lat_errs,
            'lon_errs':       lon_errs,
            'alt_errs':       alt_errs,
            'indices':        indices,
            'n_spoofed':      int(spoof_flags.sum()),
            'n_total':        len(spoof_flags),
            'risk_score':     float(spoof_flags.sum()) / max(1, len(spoof_flags)),
            'onset_index':    onset_index,
            'onset_detected': onset_index is not None,
            'lat_threshold':  self.lat_threshold,
            'lon_threshold':  self.lon_threshold,
            'alt_threshold':  self.alt_threshold,
        }

    def _find_onset(self, spoof_flags: np.ndarray, indices: list):
        """
        Trouve le premier index original où `onset_min_consecutive` points
        suspects consécutifs apparaissent. Retourne None si aucun onset.
        """
        k           = self.onset_min_consecutive
        consecutive = 0
        for i, flag in enumerate(spoof_flags):
            if flag:
                consecutive += 1
                if consecutive >= k:
                    return indices[i - k + 1]
            else:
                consecutive = 0
        return None
