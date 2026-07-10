# Conexiones LCD JHD 162A (16x2, HD44780, modo 4-bit)

## Pinout de la pantalla

```
[Display]
┌──────────────────────────────────────┐
│                                      │
└──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
   1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
  GND 5V V0 RS RW  E  -  -  -  -  D4 D5 D6 D7  A  K
```

> Pin 1 está a la **izquierda** mirando la pantalla de frente. Los pines 7–10 (DB0–DB3) no se conectan en modo 4-bit.

---

## Conexión con Arduino MKR1000

| Pin LCD | Nombre   | Conectar a       |
|---------|----------|------------------|
| 1       | VSS      | GND              |
| 2       | VDD      | 5V               |
| 3       | V0       | Potenciómetro 10kΩ (wiper) |
| 4       | RS       | Pin 5            |
| 5       | R/W      | GND              |
| 6       | E        | Pin 7            |
| 7–10    | DB0–DB3  | Sin conectar     |
| 11      | DB4      | Pin 2            |
| 12      | DB5      | Pin 3            |
| 13      | DB6      | Pin 8            |
| 14      | DB7      | Pin 9            |
| 15      | A (LED+) | 5V + resistencia 100Ω |
| 16      | K (LED–) | GND              |

```cpp
// hd44780 (usar esta en MKR1000 — LiquidCrystal falla en SAMD21)
hd44780_pinIO lcd(5, 7, 2, 3, 8, 9);
```

> El MKR1000 opera a **3.3V** pero el HD44780 detecta HIGH desde 2.2V, por lo que las señales funcionan. La pantalla se alimenta con **5V** (pin `5V` del MKR1000, disponible solo con USB conectado).
> Pin 6 es `LED_BUILTIN` — evitarlo como señal E. Pines A3/A4 tienen problemas como salidas digitales con la librería hd44780 en SAMD21 — usar pines digitales puros.

---

## Conexión con ESP32 DevKit

| Pin LCD | Nombre   | Conectar a       |
|---------|----------|------------------|
| 1       | VSS      | GND              |
| 2       | VDD      | 5V (pin VIN)     |
| 3       | V0       | Potenciómetro 10kΩ (wiper) |
| 4       | RS       | GPIO 13          |
| 5       | R/W      | GND              |
| 6       | E        | GPIO 14          |
| 7–10    | DB0–DB3  | Sin conectar     |
| 11      | DB4      | GPIO 25          |
| 12      | DB5      | GPIO 26          |
| 13      | DB6      | GPIO 27          |
| 14      | DB7      | GPIO 33          |
| 15      | A (LED+) | 5V + resistencia 100Ω |
| 16      | K (LED–) | GND              |

```cpp
LiquidCrystal lcd(13, 14, 25, 26, 27, 33);
```

> El pin **VIN** del ESP32 entrega 5V solo cuando está alimentado por USB.

---

## Potenciómetro de contraste (V0)

```
5V ──┬── [extremo 1]
     │
    [pot 10kΩ] ── wiper ──► Pin 3 (V0)
     │
GND ─┴── [extremo 2]
```

Girarlo despacio con la pantalla encendida hasta que aparezcan los caracteres. Si el contraste está muy bajo la pantalla parece apagada aunque el backlight esté encendido.

---

## Notas

- Si la pantalla está **completamente oscura**: revisar pines 15/16 (backlight) y que el 5V esté presente.
- Si hay **backlight pero sin texto**: ajustar el potenciómetro de contraste.
- Si aparecen **bloques negros en fila 1**: el contraste es correcto pero el código no inicializó la pantalla.
