import re
from typing import List, Dict, Any, Optional
from collections import Counter


class WordExtraction:
    """
    Extrahiert strukturierte Inhalte aus Word-Dokumenttext anhand definierter Tags
    und liefert ein JSON-Format sowie eine einfache Tag-Statistik.
    """

    def __init__(self):
        self.standard_tags = [
            'Titel$', 'Titel2$', 'Titel3$', 'Text$', 'Hinweis$', 'Wichtig$', 
            'Tipp$', 'Exkurs$', 'Quellen$', 'Lernziele$', 'Inhaltsverzeichnis$', 
            'Auflistung$',
        ]
        self.special_tags = ['Bild$', 'Code$']
        self.all_tags = self.standard_tags + self.special_tags

    def extract_content_to_json(self, text: str) -> Dict[str, Any]:
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
        Findet Tag in einer Zeile (auch wenn Tag Teil der Zeile ist).
        Erkennt sowohl bekannte als auch unbekannte Tags (Wörter die mit $ enden).
        
        Args:
            line: Zu prüfende Zeile
            
        Returns:
            str: Gefundener Tag oder None
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
        full_content = ' '.join(content).strip()
        if not full_content:
            return

        def split_items():
            """Extrahiert Auflistungselemente (mit Punkten, Nummerierung oder einfach Zeilen)"""
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
                    items.append(clean_line)
                else:
                    # Einfache Zeile ohne Punkt/Nummerierung
                    items.append(line)
            
            return [item for item in items if item]

        def split_paragraphs():
            """Erkennt Absätze in Texten und teilt sie auf"""
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
