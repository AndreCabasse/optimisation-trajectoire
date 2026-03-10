"""
Module de sécurité pour la détection et l'injection de spoofing
"""
from .spoofing_detector import SpoofingDetector, AnomalyType, AnomalyReport
from .spoofing_injector import SpoofingInjector, SpoofingType
from .advanced_spoofing_detector import (
    AdvancedSpoofingDetector,
    AdvancedSpoofingReport,
    SpoofingPattern
)

__all__ = [
    'SpoofingDetector',
    'AnomalyType',
    'AnomalyReport',
    'SpoofingInjector',
    'SpoofingType',
    'AdvancedSpoofingDetector',
    'AdvancedSpoofingReport',
    'SpoofingPattern'
]
