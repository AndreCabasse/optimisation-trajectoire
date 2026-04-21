import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]
from tensorflow.keras.models import Sequential  # type: ignore[import-untyped]
from tensorflow.keras.layers import LSTM, Dense, Bidirectional  # type: ignore[import-untyped]
from tensorflow.keras.optimizers import Adam  # type: ignore[import-untyped]

# =========================
# PARAMÈTRES
# =========================
CSV_PATH = "track-4B.csv"   #chemin vers le fichier CSV
WINDOW_SIZE =  75  # taille de la fenêtre temporelle
PRED_HORIZON = 10         # prédiction à n pas
EPOCHS = 50
BATCH_SIZE = 32
ALT_THRESHOLD_METERS = 500  # seuil altitude (m)
LAT_THRESHOLD_degres = 0.2    # seuil latitude (Â°)
LON_THRESHOLD_degres = 0.2   # seuil longitude (Â°)

# -------------------------
# SPOOFING SIMULATION (jump lat/lon)
# -------------------------
ENABLE_SPOOF_JUMP = False
SPOOF_JUMP_IDX = 300         # index du saut
SPOOF_JUMP_LAT_DEG = 5    # saut latitude (degrés)
SPOOF_JUMP_LON_DEG = 5   # saut longitude (degrés)

ENABLE_SPOOF_HEADING_DRIFT =False
SPOOF_DRIFT_START_IDX = 270
SPOOF_DRIFT_END_IDX = 330
SPOOF_DRIFT_MAX_DEG = 5  # variation max du cap (degrés)
SPOOF_DRIFT_APPLY_TO_HEADING = False  # met à jour la colonne heading

# =========================
# FONCTIONS UTILITAIRES
# =========================
#def haversine_distance(lat1, lon1, lat2, lon2):
#    R = 6371000.0  # rayon Terre en mètres
#    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
#    dlat = lat2 - lat1
#    dlon = lon2 - lon1
#    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
#    c = 2 * np.arcsin(np.sqrt(a))
#    return R * c

def component_errors_meters(real, pred):
    # latitude-only error: change latitude, keep longitude fixed
    lat_err = abs(real[0] - pred[0])
    # longitude-only error: change longitude, keep latitude fixed
    lon_err = abs(real[1] - pred[1])
    # altitude error
    alt_err = abs(real[2] - pred[2])
    return lat_err, lon_err, alt_err

def create_sequences(features_data, target_data, window):
    X, y = [], []
    max_i = len(features_data) - window - PRED_HORIZON
    for i in range(max_i):
        X.append(features_data[i:i+window])
        y.append(target_data[i+window])
    return np.array(X), np.array(y)

def apply_latlon_jump(df, idx, dlat_deg, dlon_deg):
    if "lat" not in df.columns or "lon" not in df.columns:
        raise ValueError("Les colonnes 'lat' et/ou 'lon' sont introuvables.")
    if idx < 0 or idx >= len(df):
        raise ValueError("SPOOF_JUMP_IDX est hors limites.")
    df = df.copy()
    df.loc[idx, "lat"] = df.loc[idx, "lat"] + dlat_deg
    df.loc[idx, "lon"] = df.loc[idx, "lon"] + dlon_deg
    return df

def apply_heading_drift(df, start_idx, end_idx, max_delta_deg, apply_to_heading=True):
    required = {"time", "lat", "lon", "speed", "heading"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Colonnes manquantes: {missing}")
    if start_idx < 1:
        start_idx = 1
    if end_idx <= start_idx or end_idx >= len(df):
        raise ValueError("SPOOF_DRIFT_END_IDX doit etre > start_idx et < len(df).")

    df = df.copy()
    time_diff = df["time"].diff()
    positive_dts = time_diff[time_diff > 0]
    default_dt = float(positive_dts.median()) if len(positive_dts) > 0 else 1.0

    r_earth = 6371000.0
    span = end_idx - start_idx

    for i in range(start_idx, len(df)):
        if start_idx <= i <= end_idx:
            progress = (i - start_idx) / span if span > 0 else 1.0
            delta_deg = max_delta_deg * np.sin(np.pi * progress)
        else:
            delta_deg = 0.0

        heading_deg = (df.loc[i, "heading"] + delta_deg) % 360.0
        if apply_to_heading and start_idx <= i <= end_idx:
            df.loc[i, "heading"] = heading_deg

        dt = df.loc[i, "time"] - df.loc[i - 1, "time"]
        if dt <= 0:
            dt = default_dt

        distance_m = df.loc[i, "speed"] * dt
        lat_prev = np.radians(df.loc[i - 1, "lat"])
        lon_prev = np.radians(df.loc[i - 1, "lon"])
        heading_rad = np.radians(heading_deg)

        dlat = (distance_m * np.cos(heading_rad)) / r_earth
        dlon = (distance_m * np.sin(heading_rad)) / (r_earth * np.cos(lat_prev))

        df.loc[i, "lat"] = np.degrees(lat_prev + dlat)
        df.loc[i, "lon"] = np.degrees(lon_prev + dlon)

    return df

# =========================
# CHARGEMENT & PRÉTRAITEMENT
# =========================
df_raw = pd.read_csv(CSV_PATH)

df_train = df_raw.copy()
df_stream = df_raw.copy()

if ENABLE_SPOOF_JUMP:
    df_stream = apply_latlon_jump(
        df_stream,
        idx=SPOOF_JUMP_IDX,
        dlat_deg=SPOOF_JUMP_LAT_DEG,
        dlon_deg=SPOOF_JUMP_LON_DEG
    )

if ENABLE_SPOOF_HEADING_DRIFT:
    df_stream = apply_heading_drift(
        df_stream,
        start_idx=SPOOF_DRIFT_START_IDX,
        end_idx=SPOOF_DRIFT_END_IDX,
        max_delta_deg=SPOOF_DRIFT_MAX_DEG,
        apply_to_heading=SPOOF_DRIFT_APPLY_TO_HEADING
    )

features = ["lat", "lon", "altitude", "speed", "heading"]
target = ["lat", "lon", "altitude"]

X_raw_train = df_train[features].values
y_raw_train = df_train[target].values

X_raw_stream = df_stream[features].values
y_raw_stream = df_stream[target].values

scaler_X = StandardScaler()
scaler_y = StandardScaler()

X_scaled_train = scaler_X.fit_transform(X_raw_train)
y_scaled_train = scaler_y.fit_transform(y_raw_train)

X_scaled_stream = scaler_X.transform(X_raw_stream)

X_seq, y_seq = create_sequences(X_scaled_train, y_scaled_train, WINDOW_SIZE)

# =========================
# MODÈLE BI-LSTM
# =========================
model = Sequential([
    Bidirectional(LSTM(64, return_sequences=False), input_shape=(WINDOW_SIZE, X_seq.shape[2])),
    Dense(32, activation="relu"),
    Dense(3)
])

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss="mse"
)

model.fit(
    X_seq,
    y_seq,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    verbose=1
)

# =========================
# PRÉDICTION EN LIGNE & DÉTECTION
# =========================
predicted_positions = []
real_positions = []
spoof_flags = []
lat_errs = []
lon_errs = []
alt_errs = []
stream_indices = []

for i in range(WINDOW_SIZE, len(X_scaled_stream) - 1):
    window = X_scaled_stream[i-WINDOW_SIZE:i]
    window = np.expand_dims(window, axis=0)

    pred_scaled = model.predict(window, verbose=0)
    pred = scaler_y.inverse_transform(pred_scaled)[0]

    real = y_raw_stream[i]
    stream_indices.append(i)

    lat_err, lon_err, alt_err = component_errors_meters(real, pred)
    lat_errs.append(lat_err)
    lon_errs.append(lon_err)
    alt_errs.append(alt_err)
    is_spoof = (
        alt_err > ALT_THRESHOLD_METERS
        or lat_err > LAT_THRESHOLD_degres
        or lon_err > LON_THRESHOLD_degres
    )

    predicted_positions.append(pred)
    real_positions.append(real)
    spoof_flags.append(is_spoof)

    if is_spoof:
        print(
            f"[SPOOFING SUSPECTÉ] time={df_stream.iloc[i]['time']} "
            f"alt_err={alt_err:.1f} m, lat_err={lat_err:.1f} m, lon_err={lon_err:.1f} m"
        )

pred_positions = np.array(predicted_positions)
real_positions_arr = np.array(real_positions)
spoof_flags_arr = np.array(spoof_flags)

df_stream_view = df_stream.iloc[stream_indices]
#print(predicted_positions)
#print(real_positions)

# =========================
# VISUALISATION 3D
# =========================
fig = plt.figure(figsize=(12, 9))
ax = fig.add_subplot(111, projection="3d")

# Trajectoire recu (potentiellement spoofe)
ax.plot(
    df_stream_view["lat"],
    df_stream_view["lon"],
    df_stream_view["altitude"],
    label="Trajectoire recu",
    color="blue",
    linewidth=2
)

# Trajectoire predite
ax.plot(
    pred_positions[:, 0],
    pred_positions[:, 1],
    pred_positions[:, 2],
    label="Trajectoire predite",
    color="orange",
    linestyle="--"
)

# Points normaux
#normal_idx = np.where(~spoof_flags_arr)[0]
#ax.scatter(pred_positions[normal_idx, 0],pred_positions[normal_idx, 1],pred_positions[normal_idx, 2],color="green",s=20,label="Points normaux")

# Points spoofés
spoof_idx = np.where(spoof_flags_arr)[0]
ax.scatter(
    pred_positions[spoof_idx, 0],
    pred_positions[spoof_idx, 1],
    pred_positions[spoof_idx, 2],
    color="red",
    s=40,
    label="Spoofing détecté"
)

ax.set_xlabel("Latitude")
ax.set_ylabel("Longitude")
ax.set_zlabel("Altitude (m)")
ax.set_title("Détection de spoofing GNSS par cohérence de trajectoire (BI-LSTM)")
ax.legend()
plt.tight_layout()
plt.show()



# =========================
# VISUALISATION ERREURS TEMPORELLES
# =========================
fig2 = plt.figure(figsize=(12, 5))

plt.plot(alt_errs, label="Erreur altitude (m)")

# Seuils

plt.axhline(ALT_THRESHOLD_METERS, color="red", linestyle="--", linewidth=1)

plt.title("Erreurs entre predit et recu altitude(streaming)")
plt.xlabel("Index temporel (stream)")
plt.ylabel("Erreur")
plt.legend()
plt.tight_layout()
plt.show()

fig3 = plt.figure(figsize=(12, 5))
plt.plot(lat_errs, label="Erreur latitude (deg)")
plt.plot(lon_errs, label="Erreur longitude (deg)")


# Seuils
plt.axhline(LAT_THRESHOLD_degres, color="green", linestyle="--", linewidth=1)
plt.axhline(LON_THRESHOLD_degres, color="green", linestyle=":", linewidth=1)


plt.title("Erreurs entre predit et recu lat et lon(streaming)")
plt.xlabel("Index temporel (stream)")
plt.ylabel("Erreur")
plt.legend()
plt.tight_layout()
plt.show()