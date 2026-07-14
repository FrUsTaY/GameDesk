from telemetry import TelemetryReader
t = TelemetryReader()
if not t._is_initialized:
    print("LibreHardwareMonitor НЕ инициализирован")
else:
    for hw in t._computer.Hardware:
        hw.Update()
        print(f"[{hw.HardwareType}] {hw.Name}")
        for s in hw.Sensors:
            print(f"    {s.SensorType} | {s.Name} = {s.Value}")
        for sub in hw.SubHardware:
            sub.Update()
            print(f"  [SUB] {sub.HardwareType} {sub.Name}")
            for s in sub.Sensors:
                print(f"      {s.SensorType} | {s.Name} = {s.Value}")
