"""
Test-Script für Word Extraction Service

Lädt Word-Datei, konvertiert zu Text und testet die Extraktion.
"""

import sys
import os
import docx
from typing import Dict, List

# Pfad zum elearning Modul hinzufügen
sys.path.append(os.path.join(os.path.dirname(__file__), 'elearning'))

from services.word_extraction import WordExtraction


def load_word_document(file_path: str) -> str:
    """
    Lädt Word-Datei und konvertiert zu Text.
    
    Args:
        file_path: Pfad zur .docx Datei
        
    Returns:
        str: Extrahierter Text
    """
    try:
        print(f"📄 Lade Word-Datei: {file_path}")
        doc = docx.Document(file_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        print(f"✅ Text erfolgreich extrahiert ({len(text)} Zeichen)")
        return text
        
    except Exception as e:
        print(f"❌ Fehler beim Laden der Word-Datei: {e}")
        return ""


def format_content_preview(content: str, max_length: int = 100) -> str:
    """
    Formatiert Content für bessere Anzeige.
    
    Args:
        content: Zu formatierender Content
        max_length: Maximale Länge für Preview
        
    Returns:
        str: Formatierter Preview
    """
    if len(content) <= max_length:
        return content
    
    return content[:max_length] + "..."


def print_extraction_results(content: Dict[str, List[str]]):
    """
    Zeigt Extraktionsergebnisse formatiert an.
    
    Args:
        content: Extrahiertes Content
    """
    print("\n" + "="*60)
    print("📊 EXTRAKTIONSERGEBNISSE")
    print("="*60)
    
    if not content:
        print("❌ Keine Tags gefunden!")
        return
    
    total_tags = len(content)
    total_content_items = sum(len(contents) for contents in content.values())
    
    print(f"🏷️  Gefundene Tags: {total_tags}")
    print(f"📝 Gesamte Inhalte: {total_content_items}")
    print()
    
    for tag, contents in content.items():
        print(f"🔖 {tag} ({len(contents)} Inhalt(e)):")
        
        for i, content_item in enumerate(contents, 1):
            preview = format_content_preview(content_item)
            print(f"   {i}. {preview}")
        
        print()


def main():
    """
    Hauptfunktion für den Test.
    """
    print("🧪 TEST: Word Extraction Service")
    print("="*50)
    
    # Word-Datei Pfad
    word_file_path = "1.1 Installation und erste Schritte.docx"
    
    # Prüfe ob Datei existiert
    if not os.path.exists(word_file_path):
        print(f"❌ Word-Datei nicht gefunden: {word_file_path}")
        print("💡 Stelle sicher, dass die Datei im Hauptordner liegt")
        return
    
    # 1. Word-Datei laden
    text = load_word_document(word_file_path)
    
    if not text:
        print("❌ Konnte Word-Datei nicht laden")
        return
    
    # 2. WordExtraction Service initialisieren
    print("\n🔄 Initialisiere WordExtraction Service...")
    extractor = WordExtraction()
    
    # 3. Content zwischen Tags extrahieren
    print("🔍 Extrahiere Content zwischen Tags...")
    content = extractor.extract_content_between_tags(text)
    
    # 4. Ergebnisse anzeigen
    print_extraction_results(content)
    
    # 5. Zusammenfassung
    print("="*60)
    print("✅ TEST ABGESCHLOSSEN")
    print("="*60)
    
    if content:
        print("🎉 Extraktion erfolgreich!")
        print("📈 Nächste Schritte:")
        print("   - Keyword-Extraktion implementieren")
        print("   - In Article.json_content speichern")
        print("   - View für Frontend erstellen")
    else:
        print("⚠️  Keine Tags gefunden - prüfe Word-Datei Format")


if __name__ == "__main__":
    main() 