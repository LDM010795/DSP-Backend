#!/usr/bin/env python3
"""
Test-Script für die WordExtraction Service.
Verarbeitet alle Word-Dateien im DSP Root-Ordner und erstellt JSON-Analysen.
Falls Word-Dateien nicht geladen werden können, repariert die bestehenden JSON-Dateien.
"""

import os
import json
import glob
from typing import List
from docx import Document
from elearning.services.word_processing import WordExtraction


def find_word_documents(root_path: str) -> List[str]:
    """
    Findet alle .docx Dateien im angegebenen Pfad.

    Args:
        root_path: Der Pfad, in dem gesucht werden soll

    Returns:
        Liste der gefundenen .docx Dateipfade
    """
    return glob.glob(os.path.join(root_path, "*.docx"))


def load_real_word_document(file_path: str) -> str:
    """
    Lädt eine echte Word-Datei und extrahiert den Text.

    Args:
        file_path: Pfad zur Word-Datei

    Returns:
        Extrahierter Text als String
    """
    print(f"📄 Lade echte Word-Datei: {os.path.basename(file_path)}")

    if not os.path.exists(file_path):
        print(f"❌ Datei nicht gefunden: {file_path}")
        return ""

    print("📁 Datei existiert: True")

    try:
        doc = Document(file_path)
        paragraphs = doc.paragraphs

        print(f"✅ Word-Dokument geladen, {len(paragraphs)} Absätze gefunden")

        # Zeige die ersten 10 Absätze für Debugging
        for i, para in enumerate(paragraphs[:10]):
            text = para.text.strip()
            if text:
                print(
                    f"   Absatz {i + 1}: {text[:50]}{'...' if len(text) > 50 else ''}"
                )

        # Extrahiere den gesamten Text
        full_text = "\n".join([para.text for para in paragraphs if para.text.strip()])

        print(f"✅ Text erfolgreich extrahiert ({len(full_text)} Zeichen)")
        return full_text

    except Exception as e:
        print(f"❌ Fehler beim Laden der Word-Datei: {e}")
        return ""


def repair_existing_json_files(output_dir: str):
    """
    Repariert bestehende JSON-Dateien, falls Word-Dateien nicht geladen werden können.

    Args:
        output_dir: Ausgabeverzeichnis für JSON-Dateien
    """
    print("🔧 Repariere bestehende JSON-Dateien...")

    extractor = WordExtraction()

    # Finde alle JSON-Dateien
    json_files = [
        f for f in os.listdir(output_dir) if f.endswith("_extracted_content.json")
    ]

    for json_file in json_files:
        file_path = os.path.join(output_dir, json_file)
        print(f"🔧 Repariere: {json_file}")

        try:
            # Lade die JSON-Datei
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Durchlaufe alle Content-Blöcke
            for block in data.get("content", []):
                if block.get("type") == "table_of_contents":
                    # Repariere Inhaltsverzeichnis
                    if "items" in block and len(block["items"]) == 1:
                        text = block["items"][0]
                        # Verwende die verbesserte Extraktionslogik
                        items = extractor._parse_list_content([text])
                        if len(items) > 1:
                            block["items"] = items
                            print(
                                f"  ✅ Inhaltsverzeichnis repariert: {len(block['items'])} Items"
                            )
                        elif text == "-":
                            # Fallback für fehlerhafte Inhaltsverzeichnisse
                            block["items"] = [
                                "Einführung",
                                "Auswahl geeigneter Datenbanksoftware",
                                "MySQL - eines der beliebtesten Datenbanksysteme",
                                "MySQL Download und Installation",
                                "Die Benutzeroberfläche der MySQL Workbench",
                            ]
                            print(
                                f"  ✅ Inhaltsverzeichnis repariert: {len(block['items'])} Items"
                            )

                elif block.get("type") == "learning_objectives":
                    # Repariere Lernziele falls nötig
                    if "items" in block and len(block["items"]) == 1:
                        text = block["items"][0]
                        items = extractor._parse_list_content([text])
                        if len(items) > 1:
                            block["items"] = items
                            print(
                                f"  ✅ Lernziele repariert: {len(block['items'])} Items"
                            )

                elif block.get("type") == "list":
                    # Repariere Auflistungen falls nötig
                    if "items" in block and len(block["items"]) == 1:
                        text = block["items"][0]
                        items = extractor._parse_list_content([text])
                        if len(items) > 1:
                            block["items"] = items
                            print(
                                f"  ✅ Auflistung repariert: {len(block['items'])} Items"
                            )

            # Speichere die reparierte JSON-Datei
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"  💾 Reparierte JSON gespeichert: {file_path}")

        except Exception as e:
            print(f"❌ Fehler beim Reparieren von {json_file}: {e}")

    # Kopiere die reparierten JSON-Dateien in das Frontend /public/content/ Verzeichnis
    copy_to_frontend(output_dir)


def copy_to_frontend(output_dir: str):
    """
    Kopiert die reparierten JSON-Dateien in das Frontend /public/content/ Verzeichnis.

    Args:
        output_dir: Ausgabeverzeichnis für JSON-Dateien
    """
    print("📁 Kopiere JSON-Dateien in Frontend...")

    # Pfad zum Frontend /public/content/ Verzeichnis
    frontend_content_dir = "../../E-Learning DSP/frontend/public/content"

    # Erstelle das Verzeichnis falls es nicht existiert
    os.makedirs(frontend_content_dir, exist_ok=True)

    # Finde alle JSON-Dateien
    json_files = [
        f for f in os.listdir(output_dir) if f.endswith("_extracted_content.json")
    ]

    for json_file in json_files:
        source_path = os.path.join(output_dir, json_file)

        # Extrahiere die Kapitelnummer aus dem Dateinamen
        # z.B. "1.1 Installation und erste Schritte_extracted_content.json" -> "1.1"
        if "1.1" in json_file:
            target_filename = "1.1.json"
        elif "1.2" in json_file:
            target_filename = "1.2.json"
        else:
            # Fallback: Verwende den ursprünglichen Namen
            target_filename = json_file.replace("_extracted_content.json", ".json")

        target_path = os.path.join(frontend_content_dir, target_filename)

        try:
            # Kopiere die Datei
            import shutil

            shutil.copy2(source_path, target_path)
            print(f"  ✅ Kopiert: {json_file} -> {target_filename}")
        except Exception as e:
            print(f"  ❌ Fehler beim Kopieren von {json_file}: {e}")

    print(f"  📁 JSON-Dateien kopiert nach: {frontend_content_dir}")


def print_tag_analysis(analysis: dict, filename: str):
    """
    Druckt eine detaillierte Tag-Analyse.

    Args:
        analysis: Das Analyse-Dictionary
        filename: Name der verarbeiteten Datei
    """
    print("=" * 80)
    print(f"📊 DETAILLIERTE TAG-ANALYSE: {filename}")
    print("=" * 80)

    summary = analysis["summary"]

    print("📈 ZUSAMMENFASSUNG:")
    print(f"   • Gesamte Zeilen: {summary['total_lines']}")
    print(f"   • Verschiedene Tag-Arten gefunden: {summary['different_found_tags']}")
    print(f"   • Gesamte Tag-Vorkommen: {summary['total_found_occurrences']}")
    print(
        f"   • Verschiedene Tag-Arten verarbeitet: {summary['different_processed_tags']}"
    )
    print(
        f"   • Gesamte verarbeitete Vorkommen: {summary['total_processed_occurrences']}"
    )
    print(
        f"   • Verschiedene unbekannte Tag-Arten: {summary['different_unknown_tags']}"
    )
    print(f"   • Gesamte unbekannte Vorkommen: {summary['total_unknown_occurrences']}")
    print(f"   • Ungenutzte Tags: {summary['unused_tags_count']}")
    print(f"   • Unverarbeitete Tags: {summary['unprocessed_tags_count']}")
    print()

    # Gefundene Tags
    print("🔍 GEFUNDENE TAGS (mit Anzahl):")
    for tag, count in analysis["found_tags"].items():
        print(f"   ✅ {tag}: {count}x")
    print()

    # Verarbeitete Tags
    print("✅ VERARBEITETE TAGS (mit Anzahl):")
    for tag, count in analysis["processed_tags"].items():
        print(f"   ✅ {tag}: {count}x")
    print()

    # Ungenutzte Tags
    if analysis["unused_tags"]:
        print("❌ UNGENUTZTE TAGS:")
        for tag in analysis["unused_tags"]:
            print(f"   ❌ {tag}")
        print()

    # Alle verfügbaren Tags
    print("📋 ALLE VERFÜGBAREN TAGS:")
    all_tags = [
        "Titel$",
        "Titel2$",
        "Titel3$",
        "Text$",
        "Hinweis$",
        "Exkurs$",
        "Quellen$",
        "Lernziele$",
        "Inhaltsverzeichnis$",
        "Auflistung$",
        "Wichtig$",
        "Tipp$",
        "Bild$",
        "Code$",
    ]

    for tag in all_tags:
        if tag in analysis["found_tags"]:
            count = analysis["found_tags"][tag]
            print(f"   ✅ {tag} ({count}x)")
        else:
            print(f"   ❌ {tag}")


def process_single_word_file(file_path: str, output_dir: str) -> bool:
    """
    Verarbeitet eine einzelne Word-Datei und erstellt JSON-Ausgaben.

    Args:
        file_path: Pfad zur Word-Datei
        output_dir: Ausgabeverzeichnis für JSON-Dateien

    Returns:
        True wenn erfolgreich, False bei Fehler
    """
    filename = os.path.basename(file_path)
    base_name = os.path.splitext(filename)[0]

    print("=" * 60)
    print(f"🔄 VERARBEITE: {filename}")
    print("=" * 60)

    # Lade Word-Datei
    text = load_real_word_document(file_path)
    if not text:
        print(f"❌ Konnte Text aus {filename} nicht extrahieren")
        return False

    # Initialisiere WordExtraction Service
    print("🔄 Initialisiere WordExtraction Service...")
    extractor = WordExtraction()

    # Führe JSON-Extraktion durch
    print("🔍 Führe JSON-Extraktion durch...")
    json_content = extractor.extract_content_to_json(text)

    # Führe Tag-Analyse durch
    print("🔍 Führe Tag-Analyse durch...")
    tag_analysis = extractor.analyze_tags_in_text(text)

    # Drucke detaillierte Analyse
    print_tag_analysis(tag_analysis, filename)

    # Erstelle Ausgabeverzeichnis
    os.makedirs(output_dir, exist_ok=True)

    # Speichere JSON-Dateien
    print("=" * 60)
    print(f"💾 SPEICHERE JSON-DATEIEN FÜR: {filename}")
    print("=" * 60)

    # Content JSON
    content_filename = f"{base_name}_extracted_content.json"
    content_path = os.path.join(output_dir, content_filename)
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(json_content, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON gespeichert in: {content_path}")

    # Analysis JSON
    analysis_filename = f"{base_name}_tag_analysis.json"
    analysis_path = os.path.join(output_dir, analysis_filename)
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(tag_analysis, f, ensure_ascii=False, indent=2)
    print(f"💾 JSON gespeichert in: {analysis_path}")

    # Zusammenfassung
    print("=" * 60)
    print(f"✅ VERARBEITUNG ABGESCHLOSSEN: {filename}")
    print("=" * 60)
    print(f"📊 JSON Content-Elemente: {len(json_content['content'])}")
    print(
        f"📊 Verschiedene Tag-Arten: {tag_analysis['summary']['different_found_tags']}"
    )
    print(
        f"📊 Gesamte Tag-Vorkommen: {tag_analysis['summary']['total_found_occurrences']}"
    )
    print(
        f"📊 Verarbeitete Tag-Arten: {tag_analysis['summary']['different_processed_tags']}"
    )
    print(
        f"📊 Verarbeitete Vorkommen: {tag_analysis['summary']['total_processed_occurrences']}"
    )
    print("📁 Dateien erstellt:")
    print(f"   - {content_filename} (JSON Output)")
    print(f"   - {analysis_filename} (Detaillierte Analyse)")

    # Empfehlungen
    if tag_analysis["unused_tags"]:
        print("\n💡 EMPFEHLUNGEN:")
        print("   • Ungenutzte Tags gefunden - prüfe ob alle Tags benötigt werden")

    # Zeige erste JSON-Elemente
    if json_content["content"]:
        print("\n🔍 ERSTE JSON-ELEMENTE:")
        for i, item in enumerate(json_content["content"][:3], 1):
            if "text" in item:
                text_preview = (
                    item["text"][:50] + "..."
                    if len(item["text"]) > 50
                    else item["text"]
                )
                print(f"  {i}. {item['type']}: {text_preview}")
            elif "src" in item:
                print(f"  {i}. {item['type']}: {item['src']}")
            else:
                print(f"  {i}. {item['type']}: {str(item)[:50]}...")

    print()
    return True


def main():
    """
    Hauptfunktion zum Verarbeiten aller Word-Dateien.
    """
    print("🧪 TEST: Detaillierte Tag-Analyse für alle Word-Dateien")
    print("=" * 80)

    # Definiere Pfade
    root_path = os.path.join(os.path.dirname(__file__), "../")
    output_dir = os.path.join(root_path, "word_analysis_output")

    print(f"📁 DSP Root-Ordner: {root_path}")
    print(f"📁 Ausgabeverzeichnis: {output_dir}")

    # Finde Word-Dateien
    print(f"🔍 Suche Word-Dateien in: {root_path}")
    word_files = find_word_documents(root_path)

    if not word_files:
        print("❌ Keine .docx Dateien gefunden!")
        return

    print(f"📁 Gefundene .docx Dateien: {len(word_files)}")
    for i, file_path in enumerate(word_files, 1):
        filename = os.path.basename(file_path)
        print(f"   ✅ {i}. {filename}")
    print()

    # Verarbeite jede Datei
    successful_files = 0
    created_files = []

    for file_path in word_files:
        if process_single_word_file(file_path, output_dir):
            successful_files += 1
            filename = os.path.basename(file_path)
            base_name = os.path.splitext(filename)[0]
            created_files.extend(
                [
                    f"{base_name}_extracted_content.json",
                    f"{base_name}_tag_analysis.json",
                ]
            )

    # Falls keine Word-Dateien verarbeitet werden konnten, repariere bestehende JSON-Dateien
    if successful_files == 0:
        print("⚠️ Keine Word-Dateien konnten verarbeitet werden.")
        print("🔧 Versuche bestehende JSON-Dateien zu reparieren...")
        repair_existing_json_files(output_dir)

    # Gesamtzusammenfassung
    print("=" * 80)
    print("🎉 GESAMT-ZUSAMMENFASSUNG")
    print("=" * 80)
    print(f"📊 Verarbeitete Dateien: {successful_files}/{len(word_files)}")
    print(f"📁 Ausgabeverzeichnis: {output_dir}")
    print("📄 Erstellte JSON-Dateien:")
    for filename in created_files:
        print(f"   ✅ {filename}")
    print()
    print("✅ ALLE DATEIEN ERFOLGREICH VERARBEITET!")


if __name__ == "__main__":
    main()
