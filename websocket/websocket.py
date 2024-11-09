from fastapi import APIRouter, WebSocket
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/test")
async def test():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Audio</title>
    </head>
    <body>
        <h1>WebSocket Audio Recorder</h1>
        <button onclick="startRecording()">Start Recording</button>
        <button onclick="stopRecording()">Stop Recording</button>
        <script>
            let mediaRecorder;
            let audioContext;
            let socket = new WebSocket("ws://localhost:8000/ws/audio");

            socket.onopen = function(event) {
                console.log("WebSocket is open now.");
            };
            reader.readAsArrayBuffer(event.data);

            socket.onclose = function(event) {
                console.log("WebSocket is closed now.");
            };

            socket.onerror = function(error) {
                console.log("WebSocket error: " + error);
            };

                let reader = new FileReader();
                reader.onload = function() {
                    let arrayBuffer = reader.result;
                    audioContext.decodeAudioData(arrayBuffer, function(buffer) {
                audioContext.decodeAudioData(arrayBuffer, function(buffer) {
                    let source = audioContext.createBufferSource();
                    source.buffer = buffer;
                    source.connect(audioContext.destination);
                    source.start(0);
                }, function(e) {
                    console.log("Error with decoding audio data" + e.err);
                });
            };

            function startRecording() {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(function(stream) {
                        if (!audioContext) {
                            audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        }
                        if (audioContext.state === 'suspended') {
                            audioContext.resume();
                        }
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = function(event) {
                            if (event.data.size > 0) {
                                socket.send(event.data);
                            }
                        };
                        mediaRecorder.start(100); // Send data every 100ms
                    })
                    .catch(function(err) {
                        console.log('The following error occurred: ' + err);
                    });
            }

            function stopRecording() {
                if (mediaRecorder) {
                    mediaRecorder.stop();
                }
            }
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            print(data)

            # Do something with the audio data @kailash-turimella

            await websocket.send_bytes(data)
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        await websocket.close()