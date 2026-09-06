import sys
import serial
import numpy as np
import struct

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- НАСТРОЙКИ ---
SERIAL_PORT = '/dev/ttyUSB0' 
BAUD_RATE = 1000000  
WINDOW_SIZE = 1024  
BLOCK_SIZE = 512    
REAL_FS = 38460.0  

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.flushInput()
except Exception as e:
    print(f"Ошибка подключения: {e}")
    sys.exit(1)

data_buffer = np.zeros(WINDOW_SIZE)

# Создаем три графика друг под другом
fig, (ax_time, ax_real, ax_imag) = plt.subplots(3, 1, figsize=(10, 9))
fig.suptitle("Сверхскоростной комплексный анализ звука с поиском пиков и фаз", fontsize=14)

# 1. График временной формы (Осциллограмма)
time_x = np.arange(WINDOW_SIZE)
line_time, = ax_time.plot(time_x, np.zeros(WINDOW_SIZE), color='silver', lw=1)
ax_time.set_xlim(0, WINDOW_SIZE)
ax_time.set_ylim(-1024, 1024)
ax_time.set_title("Форма сигнала во времени (Осциллограмма)")
ax_time.set_ylabel("Амплитуда")
ax_time.grid(True, alpha=0.4)

# Текстовое табло для топ-3 частот (вешаем на верхний график)
text_peaks = ax_time.text(0.02, 0.95, "", transform=ax_time.transAxes, 
                          va='top', fontsize=10, bbox=dict(facecolor='white', alpha=0.85, edgecolor='gray'))

# 2. График действительной части (Real) + Точки пиков по фазе Real
xf = np.fft.rfftfreq(WINDOW_SIZE, d=1/REAL_FS)
line_real, = ax_real.plot(xf, np.zeros(len(xf)), color='limegreen', lw=1.5)
scatter_real = ax_real.scatter([], [], color='red', s=80, zorder=3, label='Пиковая частота')
ax_real.set_xlim(0, REAL_FS / 2)
ax_real.set_ylim(-1024, 1024)
ax_real.set_title("Действительная часть спектра (Real) — Косинусы")
ax_real.set_ylabel("Амплитуда")
ax_real.grid(True, alpha=0.4)

# 3. График мнимой части (Imaginary) + Точки пиков по фазе Imag
line_imag, = ax_imag.plot(xf, np.zeros(len(xf)), color='coral', lw=1.5)
scatter_imag = ax_imag.scatter([], [], color='red', s=80, zorder=3)
ax_imag.set_xlim(0, REAL_FS / 2)
ax_imag.set_ylim(-1024, 1024)
ax_imag.set_title("Мнимая часть спектра (Imaginary) — Синусы")
ax_imag.set_xlabel("Частота (Гц)")
ax_imag.set_ylabel("Амплитуда")
ax_imag.grid(True, alpha=0.4)

plt.tight_layout()

def update(frame):
    global data_buffer
    
    bytes_needed = BLOCK_SIZE * 2
    if ser.in_waiting >= bytes_needed:
        raw_bytes = ser.read((ser.in_waiting // bytes_needed) * bytes_needed)
        fmt = f"<{len(raw_bytes)//2}H"
        values = list(struct.unpack(fmt, raw_bytes))
        
        values = [v for v in values if 0 <= v <= 1023]
        if values:
            if len(values) > WINDOW_SIZE:
                values = values[-WINDOW_SIZE:]
            data_buffer = np.roll(data_buffer, -len(values))
            data_buffer[-len(values):] = values

    # Математика сигналов
    signal = data_buffer - np.mean(data_buffer)
    windowed_signal = signal * np.hanning(WINDOW_SIZE)
    
    # Вычисляем комплексное БПФ
    fft_complex = np.fft.rfft(windowed_signal)
    
    fft_real = np.real(fft_complex)
    fft_imag = np.imag(fft_complex)
    fft_amplitude = np.abs(fft_complex)
    fft_phase_deg = np.angle(fft_complex, deg=True)
    
    # --- АЛГОРИТМ ПОИСКА ДОМИНИРУЮЩИХ ПИКОВ ---
    # Пропускаем первые 3 бина (0-100 Гц), чтобы игнорировать постоянный шум
    search_range = slice(3, len(fft_amplitude))
    top_indices = np.argsort(fft_amplitude[search_range])[-3:] + 3
    
    peak_info = "ТОП-3 ЧАСТОТЫ:\n"
    peak_freqs = []
    peak_reals = []
    peak_imags = []
    
    for idx in reversed(top_indices):
        amp = fft_amplitude[idx]
        if amp > 35: # Порог отсечения шума
            freq = xf[idx]
            phase = fft_phase_deg[idx]
            peak_info += f"• {freq:.1f} Гц (Ампл: {amp:.0f}, Фаза: {phase:+.1f}°)\n"
            
            # Собираем координаты точек для отображения на Real и Imag графиках
            peak_freqs.append(freq)
            peak_reals.append(fft_real[idx])
            peak_imags.append(fft_imag[idx])
            
    if not peak_freqs:
        peak_info += "Сигнал слишком слабый"
        
    # --- ОБНОВЛЕНИЕ ДАННЫХ НА ГРАФИКАХ ---
    text_peaks.set_text(peak_info.strip())
    line_time.set_ydata(signal)
    line_real.set_ydata(fft_real)
    line_imag.set_ydata(fft_imag)
    
    # Подсвечиваем точками текущие пики прямо на комплексных кривых
    if peak_freqs:
        scatter_real.set_offsets(np.c_[peak_freqs, peak_reals])
        scatter_imag.set_offsets(np.c_[peak_freqs, peak_imags])
    else:
        scatter_real.set_offsets(np.empty((0, 2)))
        scatter_imag.set_offsets(np.empty((0, 2)))
        
    return line_time, text_peaks, line_real, line_imag, scatter_real, scatter_imag

# Blit=True для сохранения бешенной скорости отрисовки
ani = FuncAnimation(fig, update, blit=True, interval=10, cache_frame_data=False)

try:
    plt.show()
finally:
    ser.close()
