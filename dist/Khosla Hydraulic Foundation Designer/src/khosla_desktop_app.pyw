from pathlib import Path
import traceback


try:
    from khosla_desktop_app import main

    main()
except Exception as exc:
    log_path = Path(__file__).with_name("khosla_error.log")
    log_path.write_text(traceback.format_exc(), encoding="utf-8")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Khosla Hydraulic Foundation Designer",
            f"The app could not start.\n\n{exc}\n\nDetails were saved to:\n{log_path}",
        )
        root.destroy()
    except Exception:
        raise
