import multiprocessing as mp
import pyaudiowpatch as pyaudio
import audioop
from RealtimeSTT import AudioToTextRecorder
import threading
import sys
from PyQt5.QtWidgets import QApplication
from frontend import MainWindow
from device_selector import DeviceSelectionWindow

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
        model='hinglish_ct2_model',
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

def main():
    print("=== Live Transcription System ===")
    
    # Create QApplication ONCE - this will be used for all GUI windows
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Show device selection window
    device_selector = DeviceSelectionWindow()
    device_info = None
    
    def on_devices_selected(selected_devices):
        nonlocal device_info
        device_info = selected_devices
    
    device_selector.devices_selected.connect(on_devices_selected)
    device_selector.show()
    
    # Wait for device selection
    app.exec_()
    
    # If no devices were selected, exit
    if device_info is None:
        print("No devices selected. Exiting.")
        return
    
    # Extract device information
    loopback_index = device_info['loopback_index']
    loopback_info = device_info['loopback_info']
    mic_index = device_info['mic_index']
    mic_info = device_info['mic_info']
    
    print(f"Selected loopback device: [{loopback_index}] {loopback_info['name']}")
    print(f"Selected microphone device: [{mic_index}] {mic_info['name']}")

    # Create new QApplication for main window (REUSE the existing one)
    # Remove this line: app = QApplication(sys.argv)
    # The QApplication already exists from above
    
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