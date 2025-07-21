
import multiprocessing as mp
import pyaudiowpatch as pyaudio
import audioop
from RealtimeSTT import AudioToTextRecorder
import threading
import sys
from PyQt5.QtWidgets import QApplication
from frontend import MainWindow

transcription_queue = mp.Queue()

def record_device(device_index, tag, channels, sample_rate, trans_queue):
    p = pyaudio.PyAudio()
    
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=1024
    )
    
    recorder = AudioToTextRecorder(
        use_microphone=False,
        model='base.en',
        spinner=False,
        silero_deactivity_detection=True,
        post_speech_silence_duration=0.2,
        beam_size=1
    )
    
    recorder.start()
    
    def transcription_worker():
        while True:
            try:
                def handle_transcription(text):
                    print(f"[{tag}] {text}")
                    trans_queue.put({"tag": tag, "text": text})
                
                recorder.text(handle_transcription)
            except Exception as e:
                print(f"[{tag}] Error: {e}")
    
    threading.Thread(target=transcription_worker, daemon=True).start()
    
    state = None
    while True:
        data = stream.read(1024, exception_on_overflow=False)
        if channels > 1:
            data = audioop.tomono(data, 2, 0.5, 0.5)
        if sample_rate != 16000:
            data, state = audioop.ratecv(data, 2, 1, sample_rate, 16000, state)
        recorder.feed_audio(data)

def choose_loopback_device():
    p = pyaudio.PyAudio()
    print("Available loopback devices:")
    loopback_devices = []
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0 and 'loopback' in info['name'].lower():
            loopback_devices.append((i, info))
            print(f" [{i}] {info['name']}")
    
    if not loopback_devices:
        print("No loopback devices found. Showing all input devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f" [{i}] {info['name']}")
    
    loopback_index = int(input("Select loopback device index for [client]: "))
    loopback_info = p.get_device_info_by_index(loopback_index)
    p.terminate()
    
    return loopback_index, loopback_info

def choose_microphone_device():
    p = pyaudio.PyAudio()
    print("\nAvailable microphone devices:")
    mic_devices = []
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0 and 'loopback' not in info['name'].lower():
            mic_devices.append((i, info))
            print(f" [{i}] {info['name']}")
    
    if not mic_devices:
        print("No microphone devices found. Showing all input devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f" [{i}] {info['name']}")
    
    mic_index = int(input("Select mic device index for [you]: "))
    mic_info = p.get_device_info_by_index(mic_index)
    p.terminate()
    
    return mic_index, mic_info

def main():
    print("=== Live Transcription System ===")
    
    # Choose audio devices
    loopback_index, loopback_info = choose_loopback_device()
    mic_index, mic_info = choose_microphone_device()
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Create main window
    window = MainWindow(transcription_queue)
    window.show()
    
    # Start transcription processes
    client_proc = mp.Process(target=record_device, args=(
        loopback_index, "client", 
        loopback_info['maxInputChannels'], 
        int(loopback_info['defaultSampleRate']),
        transcription_queue
    ))
    
    mic_proc = mp.Process(target=record_device, args=(
        mic_index, "you", 
        mic_info['maxInputChannels'], 
        int(mic_info['defaultSampleRate']),
        transcription_queue
    ))
    
    client_proc.start()
    mic_proc.start()
    
    print("✓ Transcription system ready")
    
    try:
        app.exec_()
    finally:
        client_proc.terminate()
        mic_proc.terminate()
        client_proc.join()
        mic_proc.join()
        print("System stopped")

if __name__ == '__main__':
    mp.freeze_support()
    main()
