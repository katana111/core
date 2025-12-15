"""
BiometricUpdate News Enrichment Service

Scrapes and analyzes company news from biometricupdate.com
"""

from .scraper import BiometricUpdateScraper
from .db_operations import BiometricUpdateDataOperations
from .enrichment_service import BiometricUpdateEnrichmentService, enrich_competitors_with_biometricupdate

__all__ = [
    'BiometricUpdateScraper',
    'BiometricUpdateDataOperations', 
    'BiometricUpdateEnrichmentService',
    'enrich_competitors_with_biometricupdate'
]