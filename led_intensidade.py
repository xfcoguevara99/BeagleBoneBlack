#!/usr/bin/env python3
import os, time

CHIP = "/sys/class/pwm/pwmchip0"  # ehrpwm1
CHANNEL = 0  # pwm0 = P9_14
FREQ_HZ = 200  # 200 Hz - perceptível para olho humano
STEP = 0.05  # incremento de 5% no duty cycle
DELAY = 0.1  # 100 ms entre passos

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
    try:
        w(f"{pwmN}/enable", 0)
    except:
        pass
    w(f"{pwmN}/period", period_ns)
    w(f"{pwmN}/duty_cycle", duty_ns)
    w(f"{pwmN}/enable", 1)
    return period_ns, duty_ns

def update_duty(chip, ch, freq_hz, duty_ratio):
    period_ns = int(1_000_000_000 // freq_hz)
    duty_ns = min(int(period_ns * duty_ratio), period_ns - 1)
    pwmN = f"{chip}/pwm{ch}"
    w(f"{pwmN}/duty_cycle", duty_ns)
    return duty_ns

def disable_pwm(chip, ch):
    pwmN = f"{chip}/pwm{ch}"
    try:
        w(f"{pwmN}/enable", 0)
    except:
        pass

if __name__ == "__main__":
    try:
        duty = 0.0
        increasing = True
        enable_pwm(CHIP, CHANNEL, FREQ_HZ, duty)

        print(f"PWM ON: {CHIP}/pwm{CHANNEL} -> {FREQ_HZ} Hz")
        print("Variação de intensidade do LED (Ctrl+C para parar)...")

        while True:
            if increasing:
                duty += STEP
                if duty >= 1.0:
                    duty = 1.0
                    increasing = False
            else:
                duty -= STEP
                if duty <= 0.0:
                    duty = 0.0
                    increasing = True

            duty_ns = update_duty(CHIP, CHANNEL, FREQ_HZ, duty)
            print(f"Duty cycle: {duty*100:.0f}% (duty_ns={duty_ns})")
            time.sleep(DELAY)

    except KeyboardInterrupt:
        disable_pwm(CHIP, CHANNEL)
        print("\nPWM OFF.")
