"""
Word Extraction Service für E-Learning Module

Einfache Keyword-Extraktion für Anleitung-Tags.
"""

import re
from typing import List, Dict


class WordExtraction:
    """
    Einfache Keyword-Extraktion für Anleitung-Tags.
    """
    
    def __init__(self):
        # Anleitung-Tags aus der Dokumentation
        self.tags = [
            'Titel$', 'Titel2$', 'Titel3$', 'Text$', 'Hinweis$', 'Wichtig$', 
            'Tipp$', 'Exkurs$', 'Code$', 'Bild$', 'Quellen$', 'Lernziele$',
            'Inhaltsverzeichnis$', 'Auflistung$', 'Auflitung$'
        ]
    
    def extract_content_between_tags(self, text: str) -> Dict[str, List[str]]:
        """
        Extrahiert Inhalt zwischen Tags.
        
        Args:
            text: Text mit Anleitung-Tags
            
        Returns:
            Dict: Tag -> Liste von Inhalten
        """
        result = {}
        
        for tag in self.tags:
            # Pattern für Tag$ ... Inhalt ... Tag$
            pattern = f"{tag}(.*?){tag}"
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            
            if matches:
                # Whitespace entfernen
                cleaned = [match.strip() for match in matches]
                result[tag] = cleaned
        
        return result
    
    def extract_keywords(self, text: str, max_keywords: int = 50) -> List[Dict]:
        """
        Extrahiert Keywords aus Text.
        
        Args:
            text: Zu analysierender Text
            max_keywords: Maximale Anzahl Keywords
            
        Returns:
            List[Dict]: Keywords mit Metadaten
        """
        # TODO: Implementierung der Keyword-Extraktion
        pass
