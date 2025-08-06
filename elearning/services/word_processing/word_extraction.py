import re
import json
from typing import Dict, List, Any, Optional
from collections import Counter


class WordExtraction:
    """
    Service zur Extraktion von strukturiertem Inhalt aus Word-Dokumenten.
    
    Unterstützt verschiedene Tag-Typen:
    - Normale Tags: Tag$ Content Tag$ (öffnend/schließend)
    - Spezielle Tags: Bild$ bild-name.png (selbstständig)
    - Code Tags: Code$ language$ code-content Code$ (öffnend/schließend)
    """
    
    def __init__(self):
        # Normale Tags (öffnend/schließend)
        self.tags = [
            'Titel$', 'Titel2$', 'Titel3$', 'Text$', 'Hinweis$', 'Exkurs$',
            'Quellen$', 'Lernziele$', 'Inhaltsverzeichnis$', 'Auflistung$',
            'Wichtig$', 'Tipp$'
        ]
        
        # Spezielle Tags (selbstständig, kein schließender Tag)
        self.special_tags = ['Bild$', 'Code$']
        
        # Alle verfügbaren Tags
        self.all_tags = self.tags + self.special_tags
        
        # Regex für Tag-Erkennung
        self.tag_pattern = re.compile(r'(' + '|'.join(re.escape(tag) for tag in self.all_tags) + r')')
    
    def _extract_image_name(self, line: str) -> Optional[str]:
        """
        Extrahiert den Bildnamen aus einer Zeile, die mit 'Bild$' beginnt.
        
        Args:
            line: Die zu analysierende Zeile
            
        Returns:
            Den extrahierten Bildnamen oder None
        """
        if not line.startswith('Bild$'):
            return None
        
        image_name = line.replace('Bild$', '').strip()
        if not image_name:
            return None
        
        return image_name
    
    def _extract_code_content(self, line: str) -> Optional[Dict[str, str]]:
        """
        Extrahiert die Sprache und den Code-Inhalt aus einer Zeile mit Code$ Tag.
        
        Args:
            line: Die zu analysierende Zeile
            
        Returns:
            Dictionary mit 'language' und 'code' oder None
        """
        if not line.startswith('Code$'):
            return None
        
        remaining = line.replace('Code$', '').strip()
        if not remaining:
            return None
        
        if '$' in remaining:
            language = remaining.split('$')[0].strip()
            return {
                'language': language,
                'code': ''  # Code-Inhalt wird später gesammelt
            }
        
        return None
    
    def _parse_list_content(self, content: List[str]) -> List[str]:
        """
        Parst Listen-Inhalt und teilt ihn in separate Elemente auf.
        
        Args:
            content: Liste der Inhaltszeilen
            
        Returns:
            Liste der separaten Listenelemente
        """
        if not content:
            return []
        
        # Spezielle Behandlung für Inhaltsverzeichnisse ohne Nummerierung
        # Wenn mehr als 1 Zeile und keine offensichtlichen Bullets/Nummern, 
        # dann ist es wahrscheinlich ein Inhaltsverzeichnis
        if len(content) > 1:
            # Prüfe ob es sich um ein Inhaltsverzeichnis handelt
            # (keine Bullets/Nummern am Anfang der Zeilen)
            has_bullets = False
            for line in content:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*') or 
                           re.match(r'^\d+[\.\)]', line)):
                    has_bullets = True
                    break
            
            if not has_bullets:
                # Wahrscheinlich ein Inhaltsverzeichnis - jede Zeile ist ein separates Item
                items = [line.strip() for line in content if line.strip()]
                return items
        
        # Normale Behandlung für Listen mit Bullets/Nummern
        bullet_pattern = re.compile(r'^\s*(?:[-•*]|\d+[\.\)])\s+')
        
        items = []
        current_item_lines = []
        
        for line in content:
            line = line.strip()
            if not line:
                continue
            
            # Prüfe ob diese Zeile mit einem Bullet oder einer Nummer beginnt
            if bullet_pattern.match(line):
                # Neues Item beginnt - speichere vorheriges Item
                if current_item_lines:
                    items.append(' '.join(current_item_lines).strip())
                    current_item_lines = []
                
                # Entferne Bullet/Nummer und füge Inhalt hinzu
                clean_line = bullet_pattern.sub('', line)
                current_item_lines.append(clean_line)
            else:
                # Zeile gehört zum aktuellen Item (Fortsetzung)
                current_item_lines.append(line)
        
        # Füge das letzte Item hinzu
        if current_item_lines:
            items.append(' '.join(current_item_lines).strip())
        
        # Fallback: Wenn keine Items gefunden wurden
        if not items:
            # Verwende den gesamten Text als ein Item
            items = [' '.join(content).strip()]
        
        return items
    
    def extract_content_to_json(self, text: str) -> Dict[str, Any]:
        """
        Extrahiert strukturierten Inhalt aus Word-Text und konvertiert ihn zu JSON.
        
        Args:
            text: Der zu verarbeitende Text
            
        Returns:
            Dictionary mit strukturiertem JSON-Content
        """
        if not text:
            return {"content": []}
        
        # Initialisiere das Ergebnis
        result = {
            "content": []
        }
        
        # Teile den Text in Zeilen
        lines = text.split('\n')
        
        current_tag = None
        current_content = []
        code_info = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Prüfe auf Tag-Muster
            tag_match = re.match(r'^([A-Za-zäöüßÄÖÜ]+)\$\s*(.*)$', line)
            
            if tag_match:
                # Verarbeite den vorherigen Tag
                if current_tag and current_content:
                    self._add_content_to_result(result, current_tag, current_content, code_info)
                
                # Starte neuen Tag
                current_tag = tag_match.group(1) + '$'
                current_content = [tag_match.group(2)] if tag_match.group(2) else []
                code_info = None
                
                # Spezielle Behandlung für Code-Tags
                if current_tag == 'Code$':
                    code_info = {
                        'language': 'sql',
                        'code': tag_match.group(2) if tag_match.group(2) else ''
                    }
            else:
                # Füge Zeile zum aktuellen Content hinzu
                if current_tag:
                    current_content.append(line)
                    
                    # Aktualisiere Code-Info falls nötig
                    if current_tag == 'Code$' and code_info:
                        code_info['code'] += '\n' + line
        
        # Verarbeite den letzten Tag
        if current_tag and current_content:
            self._add_content_to_result(result, current_tag, current_content, code_info)
        
        return result
    
    def _add_content_to_result(self, result: Dict, tag: str, content: List[str], code_info: Optional[Dict] = None) -> None:
        """
        Fügt den extrahierten Inhalt zum Ergebnis hinzu.
        
        Args:
            result: Das Ergebnis-Dictionary
            tag: Der erkannte Tag
            content: Der extrahierte Inhalt
            code_info: Zusätzliche Informationen für Code-Blöcke
        """
        if tag == 'Titel$':
            result["content"].append({
                "type": "title",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Titel2$':
            result["content"].append({
                "type": "title2",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Titel3$':
            result["content"].append({
                "type": "title3",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Text$':
            # Entferne "/n" aus dem Text und teile in Absätze auf
            text_content = ' '.join(content).replace('/n', '\n').strip()
            paragraphs = [p.strip() for p in text_content.split('\n') if p.strip()]
            result["content"].append({
                "type": "text",
                "paragraphs": paragraphs
            })
        elif tag == 'Bild$':
            # Extrahiere den Bildnamen aus dem Inhalt
            image_content = ' '.join(content).strip()
            # Suche nach Bildnamen (z.B. "ABB1.1.png")
            image_match = re.search(r'([A-Z]+\d+\.\d+\.png|[A-Z]+\d+\.png)', image_content)
            if image_match:
                image_name = image_match.group(1)
                result["content"].append({
                    "type": "image",
                    "src": image_name,
                    "alt": f"Bild: {image_name}"
                })
            else:
                # Fallback: Verwende den gesamten Inhalt als Bildname
                result["content"].append({
                    "type": "image",
                    "src": image_content,
                    "alt": f"Bild: {image_content}"
                })
        elif tag == 'Code$':
            if code_info:
                result["content"].append({
                    "type": "code",
                    "language": code_info.get("language", "sql"),
                    "code": code_info.get("code", ' '.join(content))
                })
            else:
                result["content"].append({
                    "type": "code",
                    "language": "sql",
                    "code": ' '.join(content)
                })
        elif tag == 'Wichtig$':
            result["content"].append({
                "type": "important",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Hinweis$':
            result["content"].append({
                "type": "hint",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Tipp$':
            result["content"].append({
                "type": "tip",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Exkurs$':
            result["content"].append({
                "type": "note",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Quellen$':
            result["content"].append({
                "type": "sources",
                "text": ' '.join(content).strip()
            })
        elif tag == 'Lernziele$':
            items = self._parse_list_content(content)
            result["content"].append({
                "type": "learning_objectives",
                "items": items
            })
        elif tag == 'Inhaltsverzeichnis$':
            items = self._parse_list_content(content)
            result["content"].append({
                "type": "table_of_contents",
                "items": items
            })
        elif tag == 'Auflistung$':
            items = self._parse_list_content(content)
            result["content"].append({
                "type": "list",
                "items": items
            })
        else:
            # Unbekannter Tag - füge als Text hinzu
            result["content"].append({
                "type": "text",
                "paragraphs": [' '.join(content).strip()]
            })
    
    def analyze_tags_in_text(self, text: str) -> Dict[str, Any]:
        """
        Analysiert die Verwendung von Tags im Text.
        
        Args:
            text: Der zu analysierende Text
            
        Returns:
            Dictionary mit Tag-Analyse
        """
        lines = text.split('\n')
        total_lines = len(lines)
        
        # Zähler für gefundene und verarbeitete Tags
        found_tags_counter = Counter()
        processed_tags_counter = Counter()
        unknown_tags_counter = Counter()
        
        # Sets für verschiedene Tag-Kategorien
        found_tags_set = set()
        processed_tags_set = set()
        unknown_tags_set = set()
        
        # Aktuelle Tag-Verarbeitung
        current_tag = None
        current_content = []
        is_first_tag = True
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Prüfe auf Tag am Anfang der Zeile
            tag_match = self.tag_pattern.match(line)
            
            if tag_match:
                tag = tag_match.group(1)
                
                # Spezielle Behandlung für Bild-Tags (selbstständig)
                if tag == 'Bild$':
                    found_tags_counter[tag] += 1
                    found_tags_set.add(tag)
                    processed_tags_counter[tag] += 1
                    processed_tags_set.add(tag)
                    continue
                
                # Spezielle Behandlung für Code-Tags
                elif tag == 'Code$':
                    # Code$ Tags werden wie normale Tags behandelt
                    # Nur öffnende Tags werden gezählt
                    if not is_first_tag and current_tag == 'Code$' and current_content:
                        # Das ist ein schließender Code-Tag, markiere als verarbeitet
                        processed_tags_counter['Code$'] += 1
                        processed_tags_set.add('Code$')
                    else:
                        # Das ist ein öffnender Code-Tag, zählen
                        found_tags_counter[tag] += 1
                        found_tags_set.add(tag)
                    current_tag = tag
                    current_content = []
                
                # Normale Tags
                elif tag in self.tags:
                    if current_tag == tag:
                        # Schließender Tag gefunden
                        if current_content:
                            processed_tags_counter[tag] += 1
                            processed_tags_set.add(tag)
                        current_tag = None
                        current_content = []
                    else:
                        # Neuer öffnender Tag
                        if current_tag and current_content:
                            # Vorheriger Tag war unvollständig
                            processed_tags_counter[current_tag] += 1
                            processed_tags_set.add(current_tag)
                        
                        found_tags_counter[tag] += 1
                        found_tags_set.add(tag)
                        current_tag = tag
                        current_content = []
                
                # Unbekannte Tags
                else:
                    unknown_tags_counter[tag] += 1
                    unknown_tags_set.add(tag)
                    current_tag = tag
                    current_content = []
                
                is_first_tag = False
            else:
                # Kein Tag - Inhalt zur aktuellen Sammlung hinzufügen
                if current_tag:
                    current_content.append(line)
        
        # Verarbeite verbleibenden Inhalt
        if current_tag and current_content:
            if current_tag in self.tags or current_tag in self.special_tags:
                processed_tags_counter[current_tag] += 1
                processed_tags_set.add(current_tag)
            else:
                unknown_tags_counter[current_tag] += 1
                unknown_tags_set.add(current_tag)
        
        # Ungenutzte Tags (in all_tags aber nicht gefunden)
        unused_tags = set(self.all_tags) - found_tags_set
        
        # Unverarbeitete Tags (gefunden aber nicht verarbeitet)
        unprocessed_tags = found_tags_set - processed_tags_set
        
        return {
            "total_lines": total_lines,
            "found_tags": dict(found_tags_counter),
            "processed_tags": dict(processed_tags_counter),
            "unknown_tags": dict(unknown_tags_counter),
            "found_tags_set": list(found_tags_set),
            "processed_tags_set": list(processed_tags_set),
            "unknown_tags_set": list(unknown_tags_set),
            "unused_tags": list(unused_tags),
            "unprocessed_tags": list(unprocessed_tags),
            "summary": {
                "total_lines": total_lines,
                "different_found_tags": len(found_tags_set),
                "total_found_occurrences": sum(found_tags_counter.values()),
                "different_processed_tags": len(processed_tags_set),
                "total_processed_occurrences": sum(processed_tags_counter.values()),
                "different_unknown_tags": len(unknown_tags_set),
                "total_unknown_occurrences": sum(unknown_tags_counter.values()),
                "unused_tags_count": len(unused_tags),
                "unprocessed_tags_count": len(unprocessed_tags)
            }
        }