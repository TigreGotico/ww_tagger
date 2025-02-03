import json
import os
import argparse
from flask import Flask, render_template, request, send_from_directory
from json_database import JsonStorage


def get_app(folder_path: str, db: JsonStorage):
    app = Flask(__name__)

    current_index = db.get("_current_index", 0)
    audio_files = []
    samples = []
    metadatas = {}
    show_tagged_samples = False
    show_untagged_samples = True

    def refresh_samples():
        nonlocal audio_files, metadatas, current_index
        if os.path.isdir(folder_path):
            audio_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
            metadatas = {f: f.replace(".wav", ".json") for f in audio_files}
            audio_files.sort()  # To ensure consistent order
        else:
            audio_files = []
            metadatas = {}

    refresh_samples()

    @app.route("/", methods=["GET", "POST"])
    def index():
        nonlocal current_index, audio_files, show_tagged_samples, show_untagged_samples, samples

        do_refresh  = request.form.get('refresh_samples', 'on') == "on"
        current_index = int(request.form.get("skip_sample", current_index + 1)) - 1

        tagged = [n for n in audio_files if db.get(n, {}).get("tag", "unknown") != "unknown"]
        untagged = [n for n in audio_files if db.get(n, {}).get("tag", "unknown") == "unknown"]

        if do_refresh or not audio_files:
            refresh_samples()
            current_index = 0
            db["_current_index"] = current_index
            samples = []
            if show_tagged_samples:
                samples += tagged
            if show_untagged_samples:
                samples += untagged

        if not len(untagged) + len(tagged):
            return render_template("index.html",
                                   audio_files=[],
                                   current_audio="",
                                   folder=folder_path,
                                   json_path=db.path,
                                   metadata={"tag": "unknown", "gender": "unknown", "noise_type": "unknown"},
                                   current_index=0)

        ww = ""
        if samples:
            file_name = samples[current_index]
            meta = os.path.join(folder_path, metadatas[file_name])
            if os.path.isfile(meta):
                with open(meta) as fi:
                    meta = json.load(fi)
                ww = meta.get("name")

        if request.method == "POST":
            if 'prev' in request.form:
                current_index -= 1
            elif 'next' in request.form:
                current_index += 1
            elif "apply_config" in request.form:
                show_tagged_samples = request.form.get('show_tagged_samples', "") == "on"
                show_untagged_samples = request.form.get('show_untagged_samples', "") == "on"
                samples = []
                if show_tagged_samples:
                    samples += tagged
                if show_untagged_samples:
                    samples += untagged
            elif samples:
                db[file_name] = {'tag': request.form.get('tag', 'unknown'),
                                 'noise_type': request.form.get('noise_type', 'unknown'),
                                 'gender': request.form.get('gender', 'unknown'),
                                 "wake_word": ww}


        if current_index >= len(samples):
           current_index = 0
        elif current_index < 0:
           current_index = len(samples) - 1


        # Load current audio file for playback
        if samples:
            current_audio = samples[current_index]
            file_name = samples[current_index]
        else:
            current_audio = None
            file_name = None

        db["_current_index"] = current_index
        db.store()

        return render_template("index.html",
                               audio_files=samples,
                               wake_word=ww,
                               current_audio=current_audio,
                               folder=folder_path,
                               json_path=db.path,
                               metadata=db.get(file_name, {"tag": "unknown",
                                                           "gender": "unknown",
                                                           "noise_type": "unknown"}),
                               current_index=current_index,
                               show_tagged_samples=show_tagged_samples,
                               show_untagged_samples=show_untagged_samples
                               )

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
