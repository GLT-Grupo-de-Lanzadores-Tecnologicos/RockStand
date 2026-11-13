# Serial protocol

The PC and the Arduino talk over a plain ASCII, line-based, request/response
protocol. The PC is always the one that starts an exchange.

- Serial settings: `115200` baud, 8N1.
- Every command is one line terminated by `\n` (a trailing `\r` is tolerated).
- Every command gets exactly one reply line.

## Commands (PC -> Arduino)

| Command        | Meaning                                 | Reply                                   |
| -------------- | --------------------------------------- | --------------------------------------- |
| `G`            | Request one measurement                 | Decimal number, e.g. `1.2345`           |
| `F:<factor>`   | Set the HX711 scale factor              | `OK`, or `ERROR:factor_invalido` if `0` |
| `R`            | Recording started (blink recording LED) | `OK`                                    |
| `S`            | Recording stopped (recording LED off)   | `OK`                                    |
| anything else  | -                                       | `ERROR:comando_desconocido`             |

## Replies (Arduino -> PC)

| Reply            | Meaning                                                          |
| ---------------- | ---------------------------------------------------------------- |
| decimal number   | Measurement in kilograms-force, 4 decimals, average of 3 samples |
| `OK`             | Command accepted                                                 |
| `ERROR:<reason>` | Command rejected                                                 |

Lines that match none of these are ignored by the application.

## Units

The firmware reports `HX711::get_units(3)`, that is
`(raw - tare_offset) / scale_factor`. With a correct scale factor this is in
**kgf**. The application converts it to newtons with standard gravity
(`9.80665 m/s^2`) and works in newtons internally.

## Timing

- The application sends `G` at most every 100 ms. The real sample rate is set
  by the firmware, because each reply averages 3 HX711 conversions: existing
  logs show about 3 samples per second (one every ~0.3 s).
- The time stamp of a sample is taken on the PC when the reply arrives; the
  firmware does not send time stamps.
- After opening the port the application waits 1 s, because opening the port
  resets most Arduino boards.
- While an `F:` command is waiting for its reply, polling is suspended so the
  next line received is unambiguously the answer to that command.

## LEDs

| LED               | Behaviour                                                         |
| ----------------- | ----------------------------------------------------------------- |
| Watchdog (`A1`)   | Blinks (500 ms) while commands arrive; solid on after 2 s of silence |
| Recording (`A3`)  | Blinks (200 ms) between `R` and `S`; otherwise off                 |

## Persistence

The scale factor lives in RAM only. At power-up the firmware uses the value
compiled into the sketch (`factorEscala = 43943.025`) and tares the load cell
with 20 samples.

## Example session

```text
PC      -> G
Arduino -> 0.0012
PC      -> G
Arduino -> 0.0009
PC      -> F:44120.50000
Arduino -> OK
PC      -> R
Arduino -> OK
PC      -> G
Arduino -> 1.5031
PC      -> S
Arduino -> OK
```
