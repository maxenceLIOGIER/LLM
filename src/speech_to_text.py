import glob
import queue
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pyaudio
import streamlit as st
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

# sys.path.append(str(Path(__file__).parents[1]))
# from app.DB_utils import Database

db_path = Path(__file__).parent.parent / "database" / "db_logsv2.db"
# bdd = Database(db_path=str(db_path))
db_sqlite = sqlite3.connect(db_path, check_same_thread=False)
cursor_db = db_sqlite.cursor()


class WhisperLiveTranscription:
    def __init__(
        self,
        model_id: str = "openai/whisper-small",
        language: str = "french",
        blacklist: list = None,
    ):
        """
        Instancie un objet WhisperLiveTranscription.

        Args:
            model_id (str, optional): Le nom du modèle whisper à utiliser.
            language (str, optional): La langue supposée du flux audio.
            blacklist (list, optional): Une liste de mots ou expressions
                                        à ne pas renvoyer dans la transcription.

            processor (WhisperProcessor): The WhisperProcessor object for pre-processing audio.
            model (WhisperForConditionalGeneration): The WhisperForConditionalGeneration model for transcription.
            is_running (bool): Whether the transcription is running or not.
            language (str): The language of the transcription.
            audio_queue (queue.Queue): The queue for storing audio chunks.
            result_queue (queue.Queue): The queue for storing the transcription results.
            transcription_queue (queue.Queue): The queue for retrieving the transcription results.
        """

        # Le device utilisé, selon la disponibilité de CUDA
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # L'objet WhisperProcessor pour le pre-process de l'audio
        self.processor = WhisperProcessor.from_pretrained(model_id)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_id).to(
            self.device
        )

        # Paramètres de configuration
        # le format du flux (pyaudio)
        self.FORMAT = pyaudio.paFloat32
        # le nombre de canaux demandé par Whisper, ici 1 donc mono
        self.CHANNELS = 1
        # la frequence d'echantillonnage utilisée par Whisper, 16kHz
        # Cela évite de devoir resampler l'audio (whipser le ferait, mais cela nécessite ffmpeg)
        self.RATE = 16000
        # la taille des chunks d'audio
        self.CHUNK = 1024
        # le temps du tampon audio
        self.RECORD_SECONDS = 3
        # le seuil de silence
        self.SILENCE_THRESHOLD = 0.001

        # Les queues pour stocker les données audio et les transcriptions
        self.audio_queue = (
            queue.Queue()
        )  # chunks audio après enregistrement et avant pré-traitement
        self.result_queue = (
            queue.Queue()
        )  # chunks audio pré-traités, prêts pour transcription
        ## // le pré-traitement n'a finalement pas été exploité dans cette version // ##
        self.transcription_queue = (
            queue.Queue()
        )  # texte et timestamp de la transcription

        # Indicateur pour savoir si l'objet est en cours d'exécution
        self.is_running = False

        # La langue du flux audio
        self.language = language

        # liste pour stocker les données audio
        self.audio_buffer = []
        # initialisation du timer, pour flusher le buffer audio
        # toutes les RECORD_SECONDS secondes (cf fonction _process_audio)
        self.last_process_time = time.time()

        # Liste de mots ou expressions à ne pas renvoyer dans la transcription
        if blacklist is not None:
            self.blacklist = blacklist
        else:
            self.blacklist = ["...", "Sous-titrage Société Radio-Canada", "Merci."]

    def start_recording(self):
        """
        Utilisée pour lancer l'enregistrement audio et la transcription.

        Cette méthode démarre un flux PyAudio pour capturer l'entrée audio depuis
        le périphérique d'entrée par défaut. Les données audio sont ensuite
        traitées dans un thread séparé pour vérifier si le niveau audio dépasse
        le seuil de silence. Si le niveau audio est supérieur au seuil, les
        données sont ajoutées dans un buffer. Ce buffer est ensuite traité
        dans un thread séparé pour générer une transcription.

        La transcription est ensuite stockée dans une file d'attente pour être
        récupérée. La méthode `get_transcription` peut ensuite être utilisée
        pour récupérer la dernière transcription.
        """

        # Initialisation du témoin d'exécution
        self.is_running = True

        # On utiliser PyAudio pour capturer l'audio
        self.p = pyaudio.PyAudio()

        def audio_callback(
            in_data: bytes,
            frame_count: int,
            time_info: Dict[str, float],
            status: int,
        ) -> tuple[bytes, int]:
            """
            Fonction callback pour le flux PyAudio entrant.

            (pyaudio demande tous les arguments même si ne les utilise pas)

            Argument utilisé :
                in_data (bytes) : Les données audio reçues du périphérique d'entrée.

            Retour :
                tuple[bytes, int] : Un tuple contenant les données audio originales et
                un indicateur indiquant la continuité du flux.

            Cette fonction est appelée par PyAudio pour chaque chunk audio reçu.
            Elle convertit les données audio de bytes en tableau NumPy
            et les place dans la file d'attente pour traitement.
            """
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            self.audio_queue.put(audio_data)
            return (in_data, pyaudio.paContinue)

        # Définition du stream audio, raccordé au callback pyaudio
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=audio_callback,
        )

        print("Recording started")
        self.stream.start_stream()

        self.process_thread = threading.Thread(target=self._process_audio)
        self.transcribe_thread = threading.Thread(target=self._transcribe_audio)
        self.process_thread.start()
        self.transcribe_thread.start()

    def _process_audio(self):
        """
        Traite et met en mémoire tampon les données audio de la file d'attente.

        Cette méthode récupère les morceaux audio de la file d'attente audio,
        vérifie si le niveau audio dépasse le seuil de silence,
        et si oui met les données audio en mémoire tampon.

        Cette mémoire est constituée d'une liste "audio_buffer".
        """

        # Boucle infinie, tant que l'objet instancié n'est pas arrêté
        while self.is_running:
            try:
                raw_chunk = self.audio_queue.get(timeout=1)
                audio_chunk = raw_chunk

                # Si le niveau audio dépasse le seuil de silence,
                # on met les données audio dans audio_buffer
                if np.max(np.abs(audio_chunk)) > self.SILENCE_THRESHOLD:
                    self.audio_buffer.extend(audio_chunk)

                # Quand on dépasse RECORD_SECONDS secondes d'enregistrement,
                # on envoie le buffer audio pour transcription,
                # et on le remet à zéro
                current_time = time.time()
                if current_time - self.last_process_time >= self.RECORD_SECONDS:
                    if self.audio_buffer:

                        # Récupération des données audio depuis le buffer
                        audio_data = np.array(self.audio_buffer)

                        # Cette queue sera ensuite traitée par le thread de transcription
                        self.result_queue.put(audio_data)

                        # RAZ du buffer
                        self.audio_buffer = []

                        # Mise à jour du timer
                        self.last_process_time = current_time
            except queue.Empty:
                continue

    def _transcribe_audio(self):
        """
        Méthode pour transcrire l'audio en texte.

        Cette méthode s'exécute dans une boucle continue tant que le programme tourne ou que la file d'attente
        n'est pas vide. Elle traite les données audio pour les convertir en texte via le modèle Whisper.

        Le processus inclut:
        - Récupération des données audio depuis la file d'attente
        - Traitement et transcription via le modèle Whisper
        - Sauvegarde de la transcription dans un fichier texte
        - Ajout de la transcription à une file d'attente dédiée

        La transcription est filtrée via une liste noire (blacklist) avant d'être sauvegardée ou transmise.
        """
        while self.is_running or not self.result_queue.empty():
            try:
                audio_data = self.result_queue.get(timeout=1)

                input_features = self.processor(
                    audio_data, sampling_rate=self.RATE, return_tensors="pt"
                ).input_features.to(self.device)

                with torch.no_grad():
                    # torch.no_grad() est utilisé dans PyTorch pour désactiver temporairement
                    # le calcul du gradient, ce qui réduit la charge mémoire et accélère les calculs
                    # lors de l'inférence ou de l'évaluation de modèles.
                    predicted_ids = self.model.generate(
                        input_features,
                        language=self.language,
                        task="transcribe",
                        max_length=448,
                        no_repeat_ngram_size=3,
                    )

                transcription = self.processor.batch_decode(
                    predicted_ids, skip_special_tokens=True
                )[0]

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {transcription}")

                # Déterminer l'id du prompt et de la session à utiliser
                # cursor_db.execute(
                #     "SELECT session_id, id_origin FROM prompt ORDER BY id_prompt DESC LIMIT 1"
                # )
                # id_session, id_origin = cursor_db.fetchone()

                # Déterminer le fichier texte à utiliser
                files = sorted(glob.glob("transcription*.txt"))
                filename = files[-1]

                # On ajoute le contenu de la transaction à la table prompt
                # timestamp = datetime.now().strftime("%H:%M:%S")
                # if not any(
                #     item.lower() == transcription.lower() for item in self.blacklist
                # ):
                #     print(f"DB {timestamp}: {transcription}")
                #     cursor_db.execute(
                #         "INSERT INTO prompt (id_prompt, session_id, id_origin, prompt, timestamp) VALUES (?, ?, ?, ?, ?)",
                #         (
                #             str(uuid.uuid4()),
                #             id_session,
                #             id_origin,
                #             transcription,
                #             timestamp,
                #         ),
                #     )
                #     db_sqlite.commit()

                # On ajoute le contenu de la transcription dans le fichier texte,
                # sauf si elle est composée d'un des éléments de la blacklist
                with open(filename, "a", encoding="utf-8") as f:
                    if not any(item == transcription for item in self.blacklist):
                        f.write(f"{transcription}\n")

                # On ajoute le contenu de la transcription dans la file,
                # sauf si elle est composée d'un des éléments de la blacklist
                if not any(item == transcription for item in self.blacklist):
                    self.transcription_queue.put(
                        {"text": transcription, "timestamp": timestamp}
                    )

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error during transcription: {e}")
                continue

    def get_transcription(
        self, block: bool = False, timeout: Optional[float] = None
    ) -> Optional[Dict[str, str]]:
        """
        Méthode utilisée pour récupérer la transcription depuis la file d'attente.

        Paramètres :
        - block (bool): Si True, on attend jusqu'à ce qu'une transcription soit disponible,
                        ou que le délai d'attente soit atteint.
        - timeout (float or None): le délai d'attente maximum pour récupérer une transcription.
                                   Ignoré si block est à False.

        Renvoie :
        - dict or None: un dico contenant le texte de la transcription et le timestamp.
        """
        try:
            if block:
                return self.transcription_queue.get(block=True, timeout=timeout)
            else:
                return self.transcription_queue.get_nowait()
        except queue.Empty:
            return None

    def stop_recording(self):
        """
        Arrête l'enregistrement et le traitement des segments audio,
        puis traite les segments audio restants dans la file d'attente.

        Si le thread de transcription est toujours actif après 7 secondes,
        on l'arrête quand même et un message d'avertissement est affiché.
        """

        print("\nEn cours d'arrêt... Traitement des derniers segments audios...")

        # Arrêt du stream audio et nettoyage PyAudio
        if hasattr(self, "stream"):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, "p"):
            self.p.terminate()

        if self.audio_buffer:
            # S'il reste des données audio dans le buffer,
            # on les place dans la queue pour les traiter
            final_audio = np.array(self.audio_buffer)
            self.result_queue.put(final_audio)

        # arrêt des threads
        self.is_running = False

        # Traiter les derniers segments audio
        while not self.audio_queue.empty():
            chunk = self.audio_queue.get()
            self.audio_buffer.extend(chunk)

        if self.audio_buffer:
            final_audio = np.array(self.audio_buffer)
            self.result_queue.put(final_audio)
            input_features = self.processor(
                final_audio, sampling_rate=self.RATE, return_tensors="pt"
            ).input_features.to(self.device)
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features, language=self.language, task="transcribe"
                )
            final_transcription = self.processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0]

            # Déterminer l'id du prompt et de la session à utiliser
            # cursor_db.execute(
            #     "SELECT session_id, id_origin FROM prompt ORDER BY id_prompt DESC LIMIT 1"
            # )
            # id_session, id_origin = cursor_db.fetchone()

            # On ajoute le contenu de la transaction à la table prompt
            # timestamp = datetime.now().strftime("%H:%M:%S")
            # if not any(
            #     item.lower() == final_transcription.lower() for item in self.blacklist
            # ):
            #     print(f"DB {timestamp}: {final_transcription}")
            #     cursor_db.execute(
            #         "INSERT INTO prompt (id_prompt, prompt, session_id, id_origin, timestamp) VALUES (?, ?, ?, ?, ?)",
            #         (
            #             str(uuid.uuid4()),
            #             final_transcription,
            #             id_session,
            #             id_origin,
            #             timestamp,
            #         ),
            #     )
            #     db_sqlite.commit()

            # Récupération du dernier fichier texte
            files = sorted(glob.glob("transcription*.txt"))
            filename = files[-1]

            # # Ecriture dans le fichier texte
            with open(filename, "a", encoding="utf-8") as f:
                if not any(item == final_transcription for item in self.blacklist):
                    f.write(f"{final_transcription}\n")

        if hasattr(self, "process_thread"):
            self.process_thread.join()
        if hasattr(self, "transcribe_thread"):
            timeout = 7
            self.transcribe_thread.join(timeout=timeout)
            if self.transcribe_thread.is_alive():
                print("Attenion, le dernier chunk audio n'a pas été transcrit")

        print("Enregistrement et transcription arrêtés")
