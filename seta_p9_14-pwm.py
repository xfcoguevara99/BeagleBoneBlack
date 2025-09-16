#!/usr/bin/env python3
import os, time

CHIP = "/sys/class/pwm/pwmchip0"  # ehrpwm1
CHANNEL = 0                       # pwm0 = P9_14
FREQ_HZ = 5                    # 1 kHz
DUTY_RATIO = 0.5                 # 50% (0.0–1.0)

def w(path, v):
    with open(path, "w") as f:
        f.write(str(v))

def enable_pwm(chip, ch, freq_hz, duty_ratio):
    period_ns = int(1_000_000_000 // freq_hz)
    duty_ns = min(int(period_ns * duty_ratio), period_ns - 1)

    pwmN = f"{chip}/pwm{ch}"
    if not os.path.isdir(pwmN):
        w(f"{chip}/export", ch)
        # aguarda criar diretório
        for _ in range(50):
            if os.path.isdir(pwmN):
                break
            time.sleep(0.01)

    # desliga para configurar
    try: w(f"{pwmN}/enable", 0)
    except: pass

    w(f"{pwmN}/period", period_ns)
    w(f"{pwmN}/duty_cycle", duty_ns)
    w(f"{pwmN}/enable", 1)
    return period_ns, duty_ns

def disable_pwm(chip, ch):
    pwmN = f"{chip}/pwm{ch}"
    try: w(f"{pwmN}/enable", 0)
    except: pass

if __name__ == "__main__":
    try:
        period_ns, duty_ns = enable_pwm(CHIP, CHANNEL, FREQ_HZ, DUTY_RATIO)
        print(f"PWM ON: {CHIP}/pwm{CHANNEL} -> {FREQ_HZ} Hz, duty {duty_ns}/{period_ns}")
        print("Ctrl+C para desligar…")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        disable_pwm(CHIP, CHANNEL)
        print("\nPWM OFF.")
