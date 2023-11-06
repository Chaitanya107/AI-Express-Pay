import picamera2
import cv2
import threading

class ImageCapture:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.camera.configure(self.camera.create_preview_configuration(main={"format": 'XRGB8888', "size": (4608,2592)}))
        self.camera.start_preview()

        self.window = cv2.namedWindow("Image Preview")

        self.stop_event = threading.Event()
        self.capture_thread = threading.Thread(target=self.capture_loop)
        self.capture_thread.start()

    def capture_loop(self):
        while not self.stop_event.is_set():
            image = self.camera.capture_file(None)

            if image is not None:
                cv2.imshow("Image Preview", image)

            key = cv2.waitKey(1)

            if key == ord('\r'):
                cv2.imwrite("image.jpg", image)

    def stop(self):
        self.stop_event.set()
        self.camera.stop_preview()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    capture = ImageCapture()

    while True:
        if cv2.getWindowProperty("Image Preview", cv2.WND_PROP_VISIBLE) < 1:
            break

    capture.stop()
