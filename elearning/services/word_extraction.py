import re
from typing import List, Dict, Any, Optional
from collections import Counter


class WordExtraction:
    """
    Extrahiert strukturierte Inhalte aus Word-Dokumenttext anhand definierter Tags
    und liefert ein JSON-Format sowie eine detaillierte Tag-Statistik.
    
    Diese Klasse verarbeitet Word-Dokumente, die mit speziellen Tags markiert sind
    (z.B. 'Titel$', 'Text$', 'Lernziele$') und konvertiert sie in ein strukturiertes
    JSON-Format für die E-Learning Plattform.
    
    Attributes:
        standard_tags (List[str]): Liste aller Standard-Tags, die in JSON umgewandelt werden
        special_tags (List[str]): Liste der Spezial-Tags (Bild$, Code$), die nur erkannt werden
        all_tags (List[str]): Kombination aus standard_tags und special_tags
    
    Example:
        >>> extractor = WordExtraction()
        >>> text = "Titel$ Mein Titel Titel$\\nText$ Mein Text Text$"
        >>> result = extractor.extract_content_to_json(text)
        >>> print(result)
        {'content': [{'type': 'title', 'level': 1, 'text': 'Mein Titel'}, ...]}
    """

    def __init__(self):
        """
        Initialisiert die WordExtraction Klasse mit allen verfügbaren Tags.
        
        Definiert die Standard-Tags (werden in JSON umgewandelt) und Spezial-Tags
        (werden nur erkannt, aber nicht verarbeitet).
        """
        self.standard_tags = [
            'Titel$', 'Titel2$', 'Titel3$', 'Text$', 'Hinweis$', 'Wichtig$', 
            'Tipp$', 'Exkurs$', 'Quellen$', 'Lernziele$', 'Inhaltsverzeichnis$', 
            'Auflistung$',
        ]
        self.special_tags = ['Bild$', 'Code$']
        self.all_tags = self.standard_tags + self.special_tags

    def extract_content_to_json(self, text: str) -> Dict[str, Any]:
        """
        Extrahiert strukturierte Inhalte aus Text und konvertiert sie in JSON-Format.
        
        Diese Methode durchläuft den Text zeilenweise, erkennt Tags und sammelt
        den Inhalt zwischen öffnenden und schließenden Tags. Der Inhalt wird
        je nach Tag-Typ in verschiedene JSON-Strukturen umgewandelt.
        
        Args:
            text (str): Der zu verarbeitende Text aus dem Word-Dokument
            
        Returns:
            Dict[str, Any]: JSON-Objekt mit der Struktur:
                {
                    "content": [
                        {"type": "title", "level": 1, "text": "..."},
                        {"type": "text", "paragraphs": ["...", "..."]},
                        {"type": "learning_goals", "items": ["...", "..."]},
                        ...
                    ]
                }
        
        Example:
            >>> extractor = WordExtraction()
            >>> text = '''
            ... Titel$ Mein Haupttitel Titel$
            ... Text$ Erster Absatz/nZweiter Absatz Text$
            ... Lernziele$ • Ziel 1 • Ziel 2 Lernziele$
            ... '''
            >>> result = extractor.extract_content_to_json(text)
            >>> print(result['content'][0]['type'])
            'title'
        
        Note:
            - Tags müssen am Anfang einer Zeile stehen
            - Jeder öffnende Tag braucht einen schließenden Tag
            - Leere Zeilen werden ignoriert
            - Unbekannte Tags werden erkannt aber nicht verarbeitet
        """
        result = {"content": []}
        lines = text.split('\n')
        current_tag = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            tag = self._find_tag(line)
            if tag:
                if current_tag and current_content:
                    self._add_content_to_result(result, current_tag, current_content)
                current_tag = tag
                current_content = []
            else:
                if current_tag:
                    current_content.append(line)

        if current_tag and current_content:
            self._add_content_to_result(result, current_tag, current_content)

        return result

    def analyze_tags_in_text(self, text: str) -> Dict[str, Any]:
        """
        Analysiert den Text und erstellt detaillierte Statistiken über gefundene Tags.
        
        Diese Methode durchläuft den Text und zählt alle gefundenen, verarbeiteten
        und unbekannten Tags. Sie unterscheidet zwischen öffnenden und schließenden
        Tags und erkennt Tippfehler in Tag-Namen.
        
        Args:
            text (str): Der zu analysierende Text aus dem Word-Dokument
            
        Returns:
            Dict[str, Any]: Detaillierte Analyse mit folgender Struktur:
                {
                    "summary": {
                        "total_lines": int,
                        "total_found_tags": int,
                        "total_found_occurrences": int,
                        "total_processed_tags": int,
                        "total_processed_occurrences": int,
                        "total_unknown_tags": int,
                        "total_unknown_occurrences": int,
                        "unused_tags": List[str],
                        "unprocessed_tags": List[str]
                    },
                    "found_tags": List[str],
                    "found_tags_count": Dict[str, int],
                    "processed_tags": List[str],
                    "processed_tags_count": Dict[str, int],
                    "unknown_tags": List[str],
                    "unknown_tags_count": Dict[str, int],
                    "unused_tags": List[str],
                    "unprocessed_tags": List[str],
                    "all_available_tags": List[str]
                }
        
        Example:
            >>> extractor = WordExtraction()
            >>> text = "Titel$ Mein Titel Titel$\\nText$ Mein Text Text$\\nAuflitung$ Fehler Auflitung$"
            >>> analysis = extractor.analyze_tags_in_text(text)
            >>> print(analysis['summary']['total_found_tags'])
            2
            >>> print(analysis['unknown_tags'])
            ['Auflitung$']
        
        Note:
            - Nur öffnende Tags werden in den Zählungen berücksichtigt
            - Unbekannte Tags sind Wörter, die mit $ enden aber nicht in all_tags sind
            - Ungenutzte Tags sind verfügbare Tags, die nicht im Text gefunden wurden
        """
        lines = text.split('\n')
        found_tags_counter = Counter()  # Zählt tatsächliche Vorkommen (nur öffnende Tags)
        found_tags_set = set()  # Verschiedene Tag-Arten
        processed_tags_counter = Counter()  # Zählt verarbeitete Vorkommen
        processed_tags_set = set()  # Verschiedene verarbeitete Tag-Arten
        unknown_tags_counter = Counter()  # Zählt unbekannte Tags
        unknown_tags_set = set()  # Verschiedene unbekannte Tag-Arten
        total_lines = len(lines)

        current_tag = None
        current_content = []
        is_first_tag = True  # Flag um zu erkennen, ob es der erste Tag ist

        for line in lines:
            line = line.strip()
            if not line:
                continue

            tag = self._find_tag(line)
            if tag:
                # Prüfe ob es ein bekannter oder unbekannter Tag ist
                if tag in self.all_tags:
                    # Bekannter Tag
                    if not is_first_tag and current_tag and current_content:
                        # Das ist ein schließender Tag, nicht zählen
                        pass
                    else:
                        # Das ist ein öffnender Tag, zählen
                        found_tags_counter[tag] += 1
                        found_tags_set.add(tag)
                else:
                    # Unbekannter Tag
                    unknown_tags_counter[tag] += 1
                    unknown_tags_set.add(tag)
                
                if current_tag and current_content:
                    if current_tag in self.all_tags:
                        processed_tags_counter[current_tag] += 1
                        processed_tags_set.add(current_tag)
                
                current_tag = tag
                current_content = []
                is_first_tag = False
            else:
                if current_tag:
                    current_content.append(line)

        if current_tag and current_content:
            if current_tag in self.all_tags:
                processed_tags_counter[current_tag] += 1
                processed_tags_set.add(current_tag)

        unused_tags = set(self.all_tags) - found_tags_set
        unprocessed_tags = found_tags_set - processed_tags_set

        return {
            "summary": {
                "total_lines": total_lines,
                "total_found_tags": len(found_tags_set),  # Verschiedene Tag-Arten
                "total_found_occurrences": sum(found_tags_counter.values()),  # Gesamte Vorkommen (nur öffnende)
                "total_processed_tags": len(processed_tags_set),  # Verschiedene verarbeitete Tag-Arten
                "total_processed_occurrences": sum(processed_tags_counter.values()),  # Gesamte verarbeitete Vorkommen
                "total_unknown_tags": len(unknown_tags_set),  # Verschiedene unbekannte Tag-Arten
                "total_unknown_occurrences": sum(unknown_tags_counter.values()),  # Gesamte unbekannte Vorkommen
                "unused_tags": list(unused_tags),
                "unprocessed_tags": list(unprocessed_tags)
            },
            "found_tags": list(found_tags_set),
            "found_tags_count": dict(found_tags_counter),  # Detaillierte Zählung (nur öffnende)
            "processed_tags": list(processed_tags_set),
            "processed_tags_count": dict(processed_tags_counter),  # Detaillierte Zählung
            "unknown_tags": list(unknown_tags_set),
            "unknown_tags_count": dict(unknown_tags_counter),  # Detaillierte Zählung unbekannter Tags
            "unused_tags": list(unused_tags),
            "unprocessed_tags": list(unprocessed_tags),
            "all_available_tags": self.all_tags
        }

    def _find_tag(self, line: str) -> Optional[str]:
        """
        Findet einen Tag in einer Zeile, auch wenn der Tag nur Teil der Zeile ist.
        
        Diese Methode sucht nach bekannten Tags aus self.all_tags und unbekannten
        Tags (Wörter die mit $ enden). Sie erkennt Tags auch wenn sie nicht alleine
        auf einer Zeile stehen.
        
        Args:
            line (str): Die zu prüfende Zeile
            
        Returns:
            Optional[str]: Gefundener Tag oder None wenn kein Tag gefunden wurde
            
        Example:
            >>> extractor = WordExtraction()
            >>> extractor._find_tag("Titel$ Mein Titel")
            'Titel$'
            >>> extractor._find_tag("Bild$ ABB1.1.png")
            'Bild$'
            >>> extractor._find_tag("Normaler Text ohne Tag")
            None
            >>> extractor._find_tag("UnbekannterTag$ mit Inhalt")
            'UnbekannterTag$'
        
        Note:
            - Erst werden bekannte Tags aus self.all_tags gesucht
            - Dann werden unbekannte Tags (Wörter mit $ am Ende) gesucht
            - Tags werden auch erkannt wenn sie Teil einer längeren Zeile sind
        """
        # Erst prüfen ob ein bekannter Tag in der Zeile steht
        for tag in self.all_tags:
            if tag in line:
                return tag
        
        # Dann prüfen ob ein unbekannter Tag in der Zeile steht (Wort das mit $ endet)
        words = line.split()
        for word in words:
            if word.endswith('$'):
                return word
        
        return None

    def _add_content_to_result(self, result: Dict, tag: str, content: List[str]) -> None:
        """
        Fügt verarbeiteten Inhalt zum Ergebnis-JSON hinzu.
        
        Diese Methode verarbeitet den gesammelten Inhalt basierend auf dem Tag-Typ
        und fügt ihn in der entsprechenden JSON-Struktur zum Ergebnis hinzu.
        Sie behandelt verschiedene Tag-Typen unterschiedlich:
        - Titel-Tags: Einfacher Text
        - Text-Tags: Aufgeteilt in Absätze
        - Listen-Tags: Aufgeteilt in Items
        - Notizen-Tags: Einfacher Text mit Variant
        
        Args:
            result (Dict): Das Ergebnis-JSON, zu dem der Inhalt hinzugefügt wird
            tag (str): Der Tag-Typ (z.B. 'Titel$', 'Text$', 'Lernziele$')
            content (List[str]): Liste der Zeilen mit dem Inhalt
            
        Note:
            - Leerer Inhalt wird ignoriert
            - Unbekannte Tags werden nicht hinzugefügt
            - Zeilenumbrüche (/n) werden in \n umgewandelt
            - Absätze werden automatisch erkannt und aufgeteilt
            - Listen werden automatisch in Items aufgeteilt
        """
        full_content = ' '.join(content).strip()
        if not full_content:
            return

        def split_items():
            """
            Extrahiert Auflistungselemente aus Listen-Tags.
            
            Erkennt verschiedene Listen-Formate:
            - Aufzählungszeichen (•, -)
            - Nummerierung (1., 2., 1), 2))
            - Einfache Zeilen ohne Formatierung
            
            Returns:
                List[str]: Liste der bereinigten Listenelemente
            """
            items = []
            
            for line in content:
                line = line.strip()
                if not line:
                    continue
                
                # Prüfe ob Zeile mit Punkt oder Nummerierung beginnt
                if (line.startswith('•') or 
                    line.startswith('-') or 
                    re.match(r'^\d+\.', line) or  # Nummerierung wie "1."
                    re.match(r'^\d+\)', line)):   # Nummerierung wie "1)"
                    
                    # Entferne Punkt/Nummerierung
                    clean_line = re.sub(r'^[•\-]\s*', '', line)  # Entferne • oder -
                    clean_line = re.sub(r'^\d+[\.\)]\s*', '', line)  # Entferne Nummerierung
                    
                    # Prüfe ob die Zeile Zeilenumbrüche enthält
                    if '\n' in clean_line or '/n' in clean_line:
                        # Ersetze /n durch \n für konsistente Verarbeitung
                        clean_line = clean_line.replace('/n', '\n')
                    
                    items.append(clean_line)
                else:
                    # Einfache Zeile ohne Punkt/Nummerierung
                    # Prüfe ob die Zeile Zeilenumbrüche enthält
                    if '\n' in line or '/n' in line:
                        # Ersetze /n durch \n für konsistente Verarbeitung
                        line = line.replace('/n', '\n')
                    
                    items.append(line)
            
            return [item for item in items if item]

        def split_paragraphs():
            """
            Erkennt und teilt Absätze in Text-Tags auf.
            
            Erkennt verschiedene Arten von Absätzen:
            - Leere Zeilen zwischen Text (Word-Absätze)
            - Zeilenumbrüche (/n) im Text
            - Echte Zeilenumbrüche (\n) im Text
            
            Returns:
                List[str]: Liste der Absätze
            """
            paragraphs = []
            current_paragraph = []
            
            for line in content:
                line = line.strip()
                if not line:
                    # Leere Zeile = neuer Absatz
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                else:
                    # Prüfe ob die Zeile Zeilenumbrüche enthält
                    if '\n' in line or '/n' in line:
                        # Zeile mit Zeilenumbrüchen aufteilen
                        # Ersetze /n durch \n für konsistente Verarbeitung
                        line = line.replace('/n', '\n')
                        sub_lines = line.split('\n')
                        for sub_line in sub_lines:
                            sub_line = sub_line.strip()
                            if sub_line:
                                current_paragraph.append(sub_line)
                            else:
                                # Leere Zeile = neuer Absatz
                                if current_paragraph:
                                    paragraphs.append(' '.join(current_paragraph))
                                    current_paragraph = []
                    else:
                        current_paragraph.append(line)
            
            # Letzten Absatz hinzufügen
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            return paragraphs

        # Mapping von Tags zu JSON-Strukturen
        mapping = {
            'Titel$': {"type": "title", "level": 1, "text": full_content},
            'Titel2$': {"type": "title", "level": 2, "text": full_content},
            'Titel3$': {"type": "title", "level": 3, "text": full_content},
            'Text$': {"type": "text", "paragraphs": split_paragraphs()},
            'Hinweis$': {"type": "note", "variant": "hinweis", "text": full_content},
            'Wichtig$': {"type": "note", "variant": "wichtig", "text": full_content},
            'Tipp$': {"type": "note", "variant": "tipp", "text": full_content},
            'Exkurs$': {"type": "note", "variant": "exkurs", "text": full_content},
            'Lernziele$': {"type": "learning_goals", "items": split_items()},
            'Inhaltsverzeichnis$': {"type": "table_of_contents", "items": split_items()},
            'Auflistung$': {"type": "list", "items": split_items()},
            'Quellen$': {"type": "sources", "items": split_items()},
            'Code$': {"type": "code", "language": "python", "code": full_content},
            'Bild$': {"type": "image", "src": full_content, "alt": "Bild"}
        }

        if tag in mapping:
            result["content"].append(mapping[tag])
