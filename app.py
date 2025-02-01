import os
import argparse
from flask import Flask, render_template, request, send_from_directory
from json_database import JsonStorage


def get_app(folder_path: str, db: JsonStorage):
    app = Flask(__name__)

    current_index = db.get("_current_index", 0)
    if os.path.isdir(folder_path):
        audio_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
        audio_files.sort()  # To ensure consistent order
    else:
        audio_files = []

    @app.route("/", methods=["GET", "POST"])
    def index():
        nonlocal current_index, folder_path, audio_files, db

        if not len(audio_files):
            return render_template("index.html",
                                   audio_files=audio_files,
                                   current_audio="",
                                   folder=folder_path,
                                   json_path=db.path,
                                   metadata={"tag": "unknown", "gender": "unknown", "silence_type": "unknown"},
                                   current_index=0)

        file_name = audio_files[current_index]

        if request.method == "POST":
            if 'prev' in request.form:
                current_index = (current_index - 1) % len(audio_files)
                file_name = audio_files[current_index]
            elif 'next' in request.form:
                current_index = (current_index + 1) % len(audio_files)
                file_name = audio_files[current_index]
            else:
                db[file_name] = {'tag': request.form.get('tag', 'unknown'),
                                 'silence_type': request.form.get('silence_type', 'unknown'),
                                 'gender': request.form.get('gender', 'unknown')}
                print(db[file_name])
                db["_current_index"] = current_index
                db.store()

        # Load current audio file for playback
        if audio_files:
            current_audio = audio_files[current_index]
        else:
            current_audio = None

        return render_template("index.html",
                               audio_files=audio_files,
                               current_audio=current_audio,
                               folder=folder_path,
                               metadata=db.get(file_name,
                                               {"tag": "unknown", "gender": "unknown", "silence_type": "unknown"}),
                               current_index=current_index)

    @app.route('/audio/<filename>')
    def audio(filename):
        # Serve the audio file to the browser for playback
        return send_from_directory(folder_path, filename)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wake Word Tagger')
    parser.add_argument('--folder', type=str, required=False, help='Path to the folder with .wav files')
    parser.add_argument('--db', type=str, required=False, help='Path to the JSON database file to store tags')
    args = parser.parse_args()
    folder = args.folder or os.path.expanduser("~/.local/share/mycroft/listener/wake_words")
    db_path = args.db or os.path.join(folder, "tags.json")
    db = JsonStorage(db_path)
    app = get_app(folder, db)
    app.run(debug=True)
