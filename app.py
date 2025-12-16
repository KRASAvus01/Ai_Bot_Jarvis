import sys
import threading
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLineEdit, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal
import speech_recognition as sr 
import pyttsx3


class RecognizerThread(QThread):
    recognized = pyqtSignal(str)
    error = pyqtSignal(str)

    def run(self):
        r = sr.Recognizer()
        # Проверяем доступность PyAudio/Microphone
        try:
            mic = sr.Microphone()
        except AttributeError:
            # Emit a short machine-readable code so UI can decide how to present it
            self.error.emit('PyAudioMissing')
            return
        except OSError as e:
            # Ошибка доступа к устройству микрофона
            self.error.emit(f'Ошибка микрофона: {e}')
            self.error.connect(lambda msg: print(msg))
            return

        with mic as source:
            try:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
                text = r.recognize_google(audio, language='ru-RU')
                self.recognized.emit(text)
            except sr.WaitTimeoutError:
                self.error.emit('Таймаут: голос не обнаружен')
            except sr.UnknownValueError:
                self.error.emit('Не удалось распознать речь')
            except sr.RequestError as e:
                self.error.emit(f'Сервис недоступен: {e}')
            except Exception as e:
                self.error.emit(str(e))


class VoiceAssistant(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AI Голосовой Помощник')
        self.resize(600, 400)

        layout = QVBoxLayout()

        self.recognized_label = QLabel('Распознанная речь:')
        layout.addWidget(self.recognized_label)

        self.recognized_text = QTextEdit()
        self.recognized_text.setReadOnly(True)
        layout.addWidget(self.recognized_text)

        h = QHBoxLayout()
        self.record_btn = QPushButton('Записать речь')
        self.record_btn.clicked.connect(self.start_listening)
        h.addWidget(self.record_btn)

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText('Введите команду вручную и нажмите Enter')
        self.manual_input.returnPressed.connect(self.manual_command)
        h.addWidget(self.manual_input)

        layout.addLayout(h)

        self.response_label = QLabel('Ответ бота:')
        layout.addWidget(self.response_label)
        layout.addSpacing(self.response_label.sizeHint().height() // 2)
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        layout.addWidget(self.response_text)

        self.setLayout(layout)

        self.engine = pyttsx3.init()
        # Optional: configure voice rate or volume
        rate = self.engine.getProperty('rate')
        self.engine.setProperty('rate', rate - 20)

        self.recognizer_thread = None

    def start_listening(self):
        self.record_btn.setEnabled(False)
        self.recognized_text.append('--- Начало записи ---')
        self.recognizer_thread = RecognizerThread()
        self.recognizer_thread.recognized.connect(self.on_recognized)
        self.recognizer_thread.error.connect(self.on_error)
        self.recognizer_thread.finished.connect(self.on_listen_finished)
        self.recognizer_thread.start()

    def on_listen_finished(self):
        self.record_btn.setEnabled(True)
        self.recognized_text.append('--- Конец записи ---')

    def on_recognized(self, text):
        self.recognized_text.append(text)
        response = self.process_command(text)
        self.show_and_speak(response)

    def on_error(self, msg):
        # Handle PyAudio missing separately to avoid trying to TTS an error
        if msg == 'PyAudioMissing' or ('pyaudio' in msg.lower() or 'pyaudio' in str(msg).lower()):
            self.recognized_text.append('Ошибка: микрофон недоступен (PyAudio)')
            self.response_text.append('PyAudio не установлен или микрофон недоступен. Установите PyAudio: `pip install pipwin` и затем `pipwin install pyaudio`, либо установите подходящий wheel. Подробнее в README.')
            self.record_btn.setEnabled(True)
            return

        self.recognized_text.append(f'Ошибка: {msg}')
        self.record_btn.setEnabled(True)
        self.show_and_speak('Извините, я не расслышал. Попробуйте ещё раз.')

    def manual_command(self):
        cmd = self.manual_input.text().strip()
        if not cmd:
            return
        self.recognized_text.append(f'Команда вручную: {cmd}')
        response = self.process_command(cmd)
        self.manual_input.clear()
        self.show_and_speak(response)

    def process_command(self, text: str) -> str:
        t = text.lower()
        if any(x in t for x in ['привет', 'здравствуй', 'добрый']):
            return 'Привет! Чем могу помочь?'
        if 'как дела' in t:
            return 'Всё отлично, спасибо! А у вас?'
        if 'время' in t:
            now = datetime.datetime.now().strftime('%H:%M')
            return f'Сейчас {now}'
        if 'дата' in t:
            today = datetime.datetime.now().strftime('%d.%m.%Y')
            return f'Сегодня {today}'
        if 'что ты умеешь' in t or 'что ты можешь' in t:
            return 'Я могу распознавать вашу речь, отвечать на простые команды и озвучивать ответы.'
        if 'спасибо' in t:
            return 'Пожалуйста!' 
        return 'Извините, я пока не знаю как ответить на это. Попробуйте другую команду.'

    def show_and_speak(self, text: str):
        self.response_text.append(text)
        # run TTS in background to avoid blocking GUI
        t = threading.Thread(target=self._speak, args=(text,))
        t.daemon = True
        t.start()

    def _speak(self, text: str):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.engine.getProperty('rate'))
            engine.say(text)
            engine.runAndWait()
        except Exception:
            # If TTS fails, write to response area
            self.response_text.append('Ошибка синтеза речи')


def main():
    app = QApplication(sys.argv)
    w = VoiceAssistant()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
