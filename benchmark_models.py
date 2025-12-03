"""
Скрипт для сравнения скорости моделей YOLO11
Benchmark script to compare YOLO11 model speeds (PyTorch vs OpenVINO)
"""

import cv2
import time
import numpy as np
from ultralytics import YOLO
import config

class ModelBenchmark:
    def __init__(self, camera_url=None):
        self.camera_url = camera_url or config.CAMERA_URL
        self.cap = None

    def connect_camera(self):
        """Подключение к камере"""
        print(f"\n📹 Подключение к камере: {self.camera_url}")
        self.cap = cv2.VideoCapture(self.camera_url)

        if not self.cap.isOpened():
            print("❌ Не удалось подключиться к камере!")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print("✅ Камера подключена!")
        return True

    def get_test_frames(self, num_frames=50):
        """Захват тестовых кадров"""
        print(f"\n📸 Захват {num_frames} тестовых кадров...")
        frames = []

        for i in range(num_frames):
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
                frames.append(frame)

            if (i + 1) % 10 == 0:
                print(f"   Захвачено {i + 1}/{num_frames} кадров")

        print(f"✅ Захвачено {len(frames)} кадров\n")
        return frames

    def benchmark_model(self, model_path, frames, model_name="Model"):
        """
        Тестирование скорости модели

        Args:
            model_path: путь к модели
            frames: список кадров для тестирования
            model_name: название модели для вывода

        Returns:
            (avg_fps, avg_inference_time)
        """
        print(f"\n{'='*60}")
        print(f"🧪 Тестирование: {model_name}")
        print(f"{'='*60}")

        # Загрузка модели
        print(f"⏳ Загрузка модели: {model_path}")
        try:
            model = YOLO(model_path)
            print(f"✅ Модель загружена успешно!")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return 0, 0

        # Прогрев модели (первые запуски обычно медленнее)
        print(f"🔥 Прогрев модели (5 кадров)...")
        for i in range(min(5, len(frames))):
            _ = model.predict(frames[i], conf=config.CONFIDENCE_THRESHOLD, verbose=False)

        # Тестирование
        print(f"⚡ Запуск бенчмарка на {len(frames)} кадрах...")
        inference_times = []
        detected_cats = 0

        start_time = time.time()

        for i, frame in enumerate(frames):
            # Замер времени инференса
            inference_start = time.time()
            results = model.predict(frame, conf=config.CONFIDENCE_THRESHOLD, verbose=False)
            inference_time = (time.time() - inference_start) * 1000  # в миллисекундах

            inference_times.append(inference_time)

            # Подсчёт детекций кота
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    if class_id == config.CAT_CLASS_ID:
                        detected_cats += 1

            # Прогресс
            if (i + 1) % 10 == 0:
                avg_time = np.mean(inference_times[-10:])
                print(f"   Кадр {i + 1}/{len(frames)} | Время: {avg_time:.1f}мс | FPS: {1000/avg_time:.1f}")

        total_time = time.time() - start_time

        # Статистика
        avg_inference = np.mean(inference_times)
        min_inference = np.min(inference_times)
        max_inference = np.max(inference_times)
        std_inference = np.std(inference_times)
        avg_fps = 1000 / avg_inference

        print(f"\n{'='*60}")
        print(f"📊 РЕЗУЛЬТАТЫ: {model_name}")
        print(f"{'='*60}")
        print(f"  Обработано кадров:        {len(frames)}")
        print(f"  Общее время:              {total_time:.2f} сек")
        print(f"  Детектировано котов:      {detected_cats}")
        print(f"\n  Среднее время инференса:  {avg_inference:.2f} мс")
        print(f"  Минимальное время:        {min_inference:.2f} мс")
        print(f"  Максимальное время:       {max_inference:.2f} мс")
        print(f"  Стандартное отклонение:   {std_inference:.2f} мс")
        print(f"\n  ⚡ Средний FPS:            {avg_fps:.2f} fps")
        print(f"{'='*60}\n")

        return avg_fps, avg_inference

    def export_to_openvino(self, model_path="yolo11n.pt"):
        """
        Экспорт модели в формат OpenVINO

        Args:
            model_path: путь к исходной модели PyTorch

        Returns:
            путь к экспортированной модели OpenVINO
        """
        print(f"\n{'='*60}")
        print(f"🔄 ЭКСПОРТ В OPENVINO")
        print(f"{'='*60}")

        try:
            print(f"⏳ Загрузка модели: {model_path}")
            model = YOLO(model_path)

            print(f"⏳ Экспорт в формат OpenVINO...")
            print(f"   (Это может занять 1-2 минуты при первом запуске)")

            # Экспорт в OpenVINO
            openvino_path = model.export(format='openvino')

            print(f"✅ Экспорт завершён успешно!")
            print(f"📁 Путь к модели OpenVINO: {openvino_path}")
            print(f"{'='*60}\n")

            return openvino_path

        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            print(f"\nВозможные причины:")
            print(f"  1. OpenVINO не установлен: pip install openvino")
            print(f"  2. Недостаточно прав для записи файлов")
            return None

    def run_comparison(self, num_frames=50):
        """
        Полное сравнение моделей PyTorch vs OpenVINO

        Args:
            num_frames: количество кадров для теста
        """
        print("\n" + "="*60)
        print("🏁 БЕНЧМАРК: YOLO11 PyTorch vs OpenVINO")
        print("="*60)
        print(f"\nПроцессор: Intel i5-1235U")
        print(f"Модель: {config.YOLO_MODEL}")
        print(f"Разрешение: {config.FRAME_WIDTH}x{config.FRAME_HEIGHT}")
        print(f"Количество тестовых кадров: {num_frames}")

        # Подключение к камере
        if not self.connect_camera():
            return

        # Захват тестовых кадров
        frames = self.get_test_frames(num_frames)

        if len(frames) < 10:
            print("❌ Недостаточно кадров для теста!")
            return

        # Тест 1: PyTorch модель
        pt_model = config.YOLO_MODEL
        pt_fps, pt_time = self.benchmark_model(pt_model, frames, "YOLO11 PyTorch (.pt)")

        # Экспорт в OpenVINO
        openvino_model = self.export_to_openvino(pt_model)

        if openvino_model is None:
            print("\n⚠️  Не удалось экспортировать в OpenVINO")
            print("Установите библиотеку: pip install openvino")
            return

        # Тест 2: OpenVINO модель
        ov_fps, ov_time = self.benchmark_model(openvino_model, frames, "YOLO11 OpenVINO")

        # Сравнение результатов
        self.print_comparison(pt_fps, pt_time, ov_fps, ov_time, openvino_model)

        # Освобождение камеры
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def print_comparison(self, pt_fps, pt_time, ov_fps, ov_time, openvino_model_path="yolo11n_openvino_model"):
        """Вывод сравнительной таблицы"""
        print("\n" + "="*60)
        print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
        print("="*60)

        speedup = ov_fps / pt_fps if pt_fps > 0 else 0
        time_reduction = ((pt_time - ov_time) / pt_time * 100) if pt_time > 0 else 0

        print(f"\n{'Модель':<25} {'FPS':<15} {'Время (мс)':<15}")
        print("-" * 60)
        print(f"{'PyTorch (.pt)':<25} {pt_fps:<15.2f} {pt_time:<15.2f}")
        print(f"{'OpenVINO':<25} {ov_fps:<15.2f} {ov_time:<15.2f}")
        print("-" * 60)
        print(f"\n⚡ Ускорение OpenVINO:      {speedup:.2f}x")
        print(f"⏱️  Снижение времени:       {time_reduction:.1f}%")

        # Рекомендация
        print(f"\n{'='*60}")
        print(f"💡 РЕКОМЕНДАЦИЯ")
        print(f"{'='*60}")

        if speedup > 1.3:
            print(f"✅ OpenVINO значительно быстрее ({speedup:.2f}x)!")
            print(f"   Рекомендуется использовать для вашего робота.")
            print(f"\n   Обновите config.py:")
            print(f'   YOLO_MODEL = "{openvino_model_path}"')
        elif speedup > 1.1:
            print(f"✅ OpenVINO немного быстрее ({speedup:.2f}x)")
            print(f"   Можно использовать для небольшего прироста скорости.")
            print(f'   YOLO_MODEL = "{openvino_model_path}"')
        else:
            print(f"⚠️  OpenVINO не даёт существенного прироста ({speedup:.2f}x)")
            print(f"   Можете оставить PyTorch модель.")

        print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("БЕНЧМАРК YOLO11: PyTorch vs OpenVINO на Intel i5-1235U")
    print("🚀" * 30 + "\n")

    # Создание бенчмарка
    benchmark = ModelBenchmark()

    # Запуск сравнения
    # num_frames - количество кадров для теста (больше = точнее, но дольше)
    benchmark.run_comparison(num_frames=50)

    print("\n✅ Бенчмарк завершён!")
    print("\nТеперь вы можете:")
    print("  1. Обновить YOLO_MODEL в config.py на более быструю версию")
    print("  2. Запустить test_detection.py для проверки детекции")
    print("  3. Запустить cat_follower_yolo11.py для следования за котом\n")
