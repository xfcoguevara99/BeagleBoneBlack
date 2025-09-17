# !/usr/bin/env python3
import os
import time
import smbus2
import sys
import termios
import tty

# Mapeamento dos sinais -> (header, gpio)
# Seu hardware informado:
# STBY=P8_9 (gpio69), AIN1=P8_7 (gpio66), AIN2=P8_19 (gpio22), BIN1=P8_11 (gpio45), BIN2=P8_13 (gpio23)
pinos = {
    "STBY": ("P8_9",  69),
    "AIN1": ("P8_7",  66),
    "AIN2": ("P8_19", 22),
    "BIN1": ("P8_11", 45),
    "BIN2": ("P8_13", 23),
}

I2C_BUS = 2          # ajuste se necessário (i2c-2)
PCA_ADDR = 0x40
# Canal do PCA para PWM dos motores (ligar PWMA/PWMB do TB6612 nesses canais)
PWM_A = 0            # PWMA -> canal 0
PWM_B = 1            # PWMB -> canal 1
PWM_LED = 8             #PWM LED Canal 8

def sh(cmd):
    os.system(cmd + " >/dev/null 2>&1")

def configurar_gpio():
    for nome, (header, gpio) in pinos.items():
        # 1) Modo do pino no header como GPIO
        sh(f"/usr/bin/config-pin {header} gpio")
        # 2) Export do GPIO (ignorar se já exportado)
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(gpio))
        except IOError:
            pass
        # 3) Direção de saída
        with open(f"/sys/class/gpio/gpio{gpio}/direction", "w") as f:
            f.write("out")

def set_gpio(nome, valor):
    _, gpio = pinos[nome]
    with open(f"/sys/class/gpio/gpio{gpio}/value", "w") as f:
        f.write("1" if valor else "0")

def aplicar_sinais(sinais):
    for nome, val in sinais.items():
        set_gpio(nome, val)

# ===== PCA9685 =====
# prescale ~= round(25e6/(4096*freq) - 1)
def pca9685_init(bus, addr=PCA_ADDR, freq_hz=1000):
    # sleep
    bus.write_byte_data(addr, 0x00, 0x10)
    prescale = int(round(25000000.0 / (4096.0 * freq_hz) - 1))
    if prescale < 3:  # limite de segurança
        prescale = 3
    bus.write_byte_data(addr, 0xFE, prescale)
    # auto-increment + ALLCALL + restart
    bus.write_byte_data(addr, 0x00, 0xA1)

def pca9685_set_pwm(bus, channel, on, off, addr=PCA_ADDR):
    base = 0x06 + 4 * channel
    bus.write_byte_data(addr, base + 0, on & 0xFF)
    bus.write_byte_data(addr, base + 1, (on >> 8) & 0x0F)
    bus.write_byte_data(addr, base + 2, off & 0xFF)
    bus.write_byte_data(addr, base + 3, (off >> 8) & 0x0F)

def pca9685_set_duty(bus, channel, duty_0_4095):
    # clamp
    d = 0 if duty_0_4095 < 0 else (4095 if duty_0_4095 > 4095 else duty_0_4095)
    if d == 0:
        # totalmente off
        pca9685_set_pwm(bus, channel, 0, 0)
    elif d == 4095:
        # totalmente on
        pca9685_set_pwm(bus, channel, 0, 4095)
    else:
        pca9685_set_pwm(bus, channel, 0, d)

# ===== Direção (TB6612) =====
def frente():
    aplicar_sinais({"STBY":1, "AIN1":1, "AIN2":0, "BIN1":1, "BIN2":0})

def tras():
    aplicar_sinais({"STBY":1, "AIN1":0, "AIN2":1, "BIN1":0, "BIN2":1})

def esquerda():
    aplicar_sinais({"STBY":1, "AIN1":1, "AIN2":0, "BIN1":0, "BIN2":1})

def direita():
    aplicar_sinais({"STBY":1, "AIN1":0, "AIN2":1, "BIN1":1, "BIN2":0})

def standby_off():
    aplicar_sinais({"STBY":0, "AIN1":0, "AIN2":0, "BIN1":0, "BIN2":0})

# ===== Leitura de tecla =====
def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def main():
    configurar_gpio()
    bus = smbus2.SMBus(I2C_BUS)

    # 1 kHz p/ TB6612
    pca9685_init(bus, PCA_ADDR, freq_hz=1000)

    # velocidade inicial (0..4095)
    duty = 2800

    # aplica duty inicial nos dois PWMs
    pca9685_set_duty(bus, PWM_A, duty)
    pca9685_set_duty(bus, PWM_B, duty)

    print("Comandos: w=frente, s=trás, a=esquerda, d=direita, x=parar,")
    print("          +/-=mais/menos velocidade, q=sair")
    print(f"Velocidade atual (0..4095): {duty}")

    try:
        while True:
            k = get_key()
            if k == 'w':
                frente();   print("Frente")
            elif k == 's':
                tras();     print("Trás")
            elif k == 'a':
                esquerda(); print("Esquerda")
            elif k == 'd':
                direita();  print("Direita")
            elif k == 'x':
                standby_off(); print("Parar / STBY=0")
            elif k == '+':
                duty = min(4095, duty + 200)
                pca9685_set_duty(bus, PWM_A, duty)
                pca9685_set_duty(bus, PWM_B, duty)
                print(f"Velocidade: {duty}")
            elif k == '-':
                duty = max(0, duty - 200)
                pca9685_set_duty(bus, PWM_A, duty)
                pca9685_set_duty(bus, PWM_B, duty)
                print(f"Velocidade: {duty}")
            elif k == 'i':
                duty_led = 4095
                pca9685_set_duty(bus, PWM_LED, duty_led)
                print("LED ligado")
            elif k == 'o':
                duty_led = 0
                pca9685_set_duty(bus, PWM_LED, duty_led)
                print("LED desligado")
            elif k == 'k':
                duty_led = min(4095, int(duty_led * 1.2))  # Aumenta 20%
                pca9685_set_duty(bus, PWM_LED, duty_led)
                print(f"Intensidade do LED aumentada para: {duty_led}")
            elif k == 'l':
                duty_led = min(4095, int(duty_led * 0.8))  # diminui 20%
                pca9685_set_duty(bus, PWM_LED, duty_led)
                print(f"Intensidade do LED diminuida para para: {duty_led}")
            elif k == 'q':
                standby_off(); print("Saindo...")
                break
    except KeyboardInterrupt:
        standby_off()
    finally:
        bus.close()

if __name__ == "__main__":
    main()