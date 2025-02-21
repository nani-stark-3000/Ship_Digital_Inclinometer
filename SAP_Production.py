import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import threading
import time
import queue
import os
import subprocess
import platform

# Allowed serial number
ALLOWED_SERIAL_NUMBER = ""  # Replace with your device's serial number

def get_device_serial_number():
    """Retrieve the device's hard drive serial number based on platform."""
    try:
        system_type = platform.system()
        if system_type == "Windows":
            result = subprocess.check_output("wmic diskdrive get serialnumber", shell=True)
            serial_number = result.decode().strip().split("\n")[1].strip()
        elif system_type == "Linux":
            result = subprocess.check_output("cat /proc/cpuinfo | grep Serial", shell=True)
            serial_number = result.decode().strip().split(": ")[-1]
        elif system_type == "Darwin":  # macOS
            result = subprocess.check_output("ioreg -l | grep IOPlatformSerialNumber", shell=True)
            serial_number = result.decode().strip().split("\"")[-2]
        else:
            print("Unsupported platform!")
            return None
        
        return serial_number
    except Exception as e:
        print(f"Error retrieving serial number: {e}")
        return None

def authenticate_device(allowed_serial_number):
    """Authenticate the device based on its serial number."""
    device_serial_number = get_device_serial_number()
    if device_serial_number != allowed_serial_number:
        print("Unauthorized device. Exiting...")
        exit(1)
    print("Device authenticated successfully.")

class PortSelector:
    def __init__(self, parent):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Select Serial Port")
        self.dialog.geometry("800x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()  # Make the dialog modal
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'+{x}+{y}')
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add refresh button
        refresh_btn = ctk.CTkButton(main_frame, text="Refresh Ports", command=self.refresh_ports)
        refresh_btn.pack(pady=(0, 10))
        
        # Create a custom table using CTkFrames and CTkLabels
        self.table_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True)
        
        # Define columns
        self.columns = ('Port', 'Description', 'Hardware ID')
        self.rows = []  # To store rows dynamically
        self.selected_row = None  # Track the currently selected row
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # Add buttons
        ctk.CTkButton(btn_frame, text="Connect", command=self.on_connect).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel).pack(side="left")
        
        self.selected_port = None
        self.refresh_ports()
    
    def refresh_ports(self):
        """Scan and refresh the list of available ports"""
        # Clear all existing widgets in the table_frame
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Clear the rows list
        self.rows.clear()

        # Get available ports
        ports = serial.tools.list_ports.comports()

        # Add header row
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="gray20")
        header_frame.pack(fill="x", pady=(0, 5))
        for i, col in enumerate(self.columns):
            header_label = ctk.CTkLabel(header_frame, text=col, font=("Helvetica", 12, "bold"), anchor="w", width=150)
            header_label.grid(row=0, column=i, padx=5, sticky="w")

        # Add port rows
        for port in ports:
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=(0, 5))

            # Add columns for each row
            ctk.CTkLabel(row_frame, text=port.device, anchor="w", width=150).grid(row=0, column=0, padx=5, sticky="w")
            ctk.CTkLabel(row_frame, text=port.description, anchor="w", width=300).grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(row_frame, text=port.hwid, anchor="w", width=300).grid(row=0, column=2, padx=5, sticky="w")

            # Store the row frame and bind click event
            row_frame.bind("<Button-1>", lambda event, r=row_frame, p=port.device: self.select_row(r, p))
            for widget in row_frame.winfo_children():
                widget.bind("<Button-1>", lambda event, r=row_frame, p=port.device: self.select_row(r, p))

            self.rows.append(row_frame)
    
    def select_row(self, row, port):
        """Handle row selection"""
        if self.selected_row:
            self.selected_row.configure(fg_color="transparent")  # Deselect previous row
        self.selected_row = row
        self.selected_port = port
        row.configure(fg_color="#0060AA")  # Highlight selected row
    
    def on_connect(self):
        """Handle port selection"""
        if not self.selected_port:
            CTkMessagebox(title="Warning", message="Please select a port first!", icon="warning")
            return
        
        self.dialog.destroy()
    
    def on_cancel(self):
        """Handle dialog cancellation"""
        self.selected_port = None
        self.dialog.destroy()

class ShipTiltDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Ship Tilt Dashboard")
        
        # Base font size for responsiveness
        self.base_font_size = 12
        
        # Fixed initial window size
        self.root.geometry("1200x800")
        self.root.configure(bg="black")

        # Create main container
        self.container = ctk.CTkFrame(root, fg_color="black")
        self.container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Initialize port selection
        port_selector = PortSelector(root)
        self.root.wait_window(port_selector.dialog)
        
        if not port_selector.selected_port:
            CTkMessagebox(title="Error", message="No port selected. Application will close.", icon="cancel")
            root.destroy()
            return
            
        try:
            self.serial_port = serial.Serial(port_selector.selected_port, 9600, timeout=1)
            CTkMessagebox(title="Success", message=f"Connected to port: {port_selector.selected_port}", icon="info")
        except Exception as e:
            CTkMessagebox(title="Connection Error", message=str(e), icon="cancel")
            root.destroy()
            return

        # Rest of your existing initialization code...
        self.tilt_angle_1 = 0  # Roll
        self.tilt_angle_2 = 0  # Pitch
        
        # Constants matching Arduino
        self.RESOLUTION_FACTOR = 364
        self.MAX_ANGLE = 90
        self.MIN_ANGLE = -90
            
        # Packet constants
        self.HEADER_HIGH = 0x5A
        self.HEADER_LOW = 0xA5
        self.PACKET_SIZE = 32
        self.TERMINATOR = 0xAA

       # Load and resize logos
        logo1_path = "logo1.png"  # Replace with your first logo file path
        logo2_path = "logo2.png"  # Replace with your second logo file path

        if os.path.exists(logo1_path) and os.path.exists(logo2_path):
            from customtkinter import CTkImage  # Import CTkImage

            # Resize logo1
            logo1_image = Image.open(logo1_path)
            resized_logo1 = logo1_image.resize((150, 200), Image.Resampling.LANCZOS)  # Adjust size as needed
            self.logo1 = CTkImage(light_image=resized_logo1, dark_image=resized_logo1, size=(150, 200))

            # Resize logo2
            logo2_image = Image.open(logo2_path)
            resized_logo2 = logo2_image.resize((150, 200), Image.Resampling.LANCZOS)  # Adjust size as needed
            self.logo2 = CTkImage(light_image=resized_logo2, dark_image=resized_logo2, size=(150, 200))
        else:
            print(f"One or both logo files not found: {logo1_path}, {logo2_path}")
            self.logo1 = None
            self.logo2 = None

        self.console_queue = queue.Queue()
        self.last_console_update = time.time()
        self.console_update_interval = 0.5
        self.start_console_thread()

        # Initialize layout
        self.init_layout()
        
        # Bind resize event
        self.root.bind("<Configure>", self.on_resize)

        # Start thread to read serial data
        self.running = True
        self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
        self.serial_thread.start()

        # Update display continuously
        self.update_interval = 16
        self.last_update = time.time()
        self.update_display()

    def init_layout(self):
        # Title and Logo Frame
        title_frame = ctk.CTkFrame(self.container, fg_color="black")
        title_frame.pack(fill="x", pady=(0, 30))

        # Left Logo (logo1)
        if self.logo1:
            self.left_logo_label = ctk.CTkLabel(title_frame, image=self.logo1, text="")
            self.left_logo_label.pack(side="left", padx=(0, 10))

        # Heading with enhanced styling
        self.heading = ctk.CTkLabel(
            title_frame,
            text="DIGITAL INCLINOMETER",
            font=("Helvetica", self.base_font_size * 6, "bold"),
            text_color="#FFFFFF"
        )
        self.heading.pack(side="left", expand=True)

        # Right Logo (logo2)
        if self.logo2:
            self.right_logo_label = ctk.CTkLabel(title_frame, image=self.logo2, text="")
            self.right_logo_label.pack(side="right", padx=(10, 0))

        # Main Frame (contains both ship displays)
        main_frame = ctk.CTkFrame(self.container, fg_color="black")
        main_frame.pack(expand=True, fill="both")

        # Create displays
        self.ship1_display = self.create_display(main_frame, "meter1.png", "ship1.png", "highlighter.png")
        self.ship1_display["frame"].pack(side="left", expand=True, fill="both")

        # Separator
        separator = ctk.CTkFrame(main_frame, width=2, fg_color="white")
        separator.pack(side="left", fill="y", padx=20)

        self.ship2_display = self.create_display(main_frame, "meter2.png", "ship2.png", "highlighter.png")
        self.ship2_display["frame"].pack(side="left", expand=True, fill="both")

    def get_angle_color(self, angle):
        """Determine color based on angle and sign."""
        if angle > 0:
            return "#00FF00"  # Green for positive angles
        elif angle < 0:
            return "#FF0000"  # Red for negative angles
        else:
            return "#FFFFFF"  # White for zero

    def create_display(self, parent, meter_img, ship_img, highlighter_img):
        """Create a single ship display using original image sizes."""
        frame = ctk.CTkFrame(parent, fg_color="black")

        # Load images with original sizes
        meter = Image.open(meter_img)
        ship = Image.open(ship_img)
        highlighter = Image.open(highlighter_img)

        # Convert to Tkinter images
        meter_tk = ImageTk.PhotoImage(meter)
        ship_tk = ImageTk.PhotoImage(ship)
        highlighter_tk = ImageTk.PhotoImage(highlighter)

        # Store references to prevent garbage collection
        frame.meter_tk = meter_tk
        frame.ship_tk = ship_tk
        frame.highlighter_tk = highlighter_tk

        # Create canvas with original image size
        canvas = ctk.CTkCanvas(frame,
                            width=meter.width,
                            height=meter.height,
                            bg="black",
                            highlightthickness=0)
        canvas.pack(expand=True) 

        # Calculate center position
        center_x = meter.width // 2
        center_y = meter.height // 2

        # Create image objects at center
        canvas.create_image(center_x, center_y, image=meter_tk, tags="meter")
        highlighter_canvas_obj = canvas.create_image(center_x, center_y, image=highlighter_tk, tags="highlighter")
        ship_canvas_obj = canvas.create_image(center_x, center_y, image=ship_tk, tags="ship")

        # Status display frame
        status_frame = ctk.CTkFrame(frame, fg_color="black")
        status_frame.pack(pady=20)

        # Enhanced angle display
        angle_label = ctk.CTkLabel(status_frame, 
                                text="0°", 
                                font=("Helvetica", 72, "bold"), 
                                text_color="#00FF00",
                                fg_color="black")
        angle_label.pack()

        return {
            "frame": frame,
            "canvas": canvas,
            "meter_img": meter,
            "meter_tk": meter_tk,
            "ship_img": ship,
            "ship_tk": ship_tk,
            "highlighter_img": highlighter,
            "highlighter_tk": highlighter_tk,
            "ship_canvas_obj": ship_canvas_obj,
            "highlighter_canvas_obj": highlighter_canvas_obj,
            "angle_label": angle_label,
            "center": (center_x, center_y)
        }

    def on_resize(self, event):
        """Handle window resize events."""
        if event.widget == self.root:
            # Update base font size based on window width
            new_font_size = max(12, int(event.width / 100))
            self.base_font_size = new_font_size

            # Update heading font size
            self.heading.configure(font=("Helvetica", self.base_font_size * 6, "bold"))

            # Resize logos
            if self.logo1:
                resized_logo1 = self.logo1._light_image.resize(
                    (int(event.width / 12), int(event.width / 12 * (200 / 150))),  # Maintain aspect ratio
                    Image.Resampling.LANCZOS
                )
                self.logo1 = ctk.CTkImage(light_image=resized_logo1, dark_image=resized_logo1, size=(int(event.width / 12), int(event.width / 12 * (200 / 150))))
                self.left_logo_label.configure(image=self.logo1)

            if self.logo2:
                resized_logo2 = self.logo2._light_image.resize(
                    (int(event.width / 12), int(event.width / 12 * (200 / 150))),  # Maintain aspect ratio
                    Image.Resampling.LANCZOS
                )
                self.logo2 = ctk.CTkImage(light_image=resized_logo2, dark_image=resized_logo2, size=(int(event.width / 12), int(event.width / 12 * (200 / 150))))
                self.right_logo_label.configure(image=self.logo2)

            # Resize main frame and its contents
            for display in [self.ship1_display, self.ship2_display]:
                self.resize_display(display, event.width, event.height)

    def resize_display(self, display, window_width, window_height):
        """Resize the display frame and its contents based on window dimensions."""
        scale_factor = window_width / 1200  # Assuming 1200 is the initial window width
        
        # Resize main frame dimensions
        frame_width = int(window_width * 0.4)  # 50% of window width
        frame_height = int(window_height * 0.8)  # 90% of window height
        display["frame"].configure(width=frame_width, height=frame_height)
        
        # Resize canvas dimensions
        canvas_width = int(frame_width * 0.9)  # 90% of frame width
        canvas_height = int(frame_height * 0.7)  # 70% of frame height
        display["canvas"].config(width=canvas_width, height=canvas_height)
        
        # Resize meter image
        if "meter_img" in display:
            resized_meter = display["meter_img"].resize(
                (int(canvas_width), int(canvas_height)),  # Fit within canvas dimensions
                Image.Resampling.LANCZOS
            )
            display["meter_tk"] = ImageTk.PhotoImage(resized_meter)
            display["canvas"].itemconfig("meter", image=display["meter_tk"])
        
        # Resize ship image
        resized_ship = display["ship_img"].resize(
            (int(canvas_width), int(canvas_height)),  # Fit within canvas dimensions
            Image.Resampling.LANCZOS
        )
        display["ship_tk"] = ImageTk.PhotoImage(resized_ship)
        display["canvas"].itemconfig("ship", image=display["ship_tk"])
        
        # Resize highlighter image
        resized_highlighter = display["highlighter_img"].resize(
            (int(canvas_width), int(canvas_height)),  # Fit within canvas dimensions
            Image.Resampling.LANCZOS
        )
        display["highlighter_tk"] = ImageTk.PhotoImage(resized_highlighter)
        display["canvas"].itemconfig("highlighter", image=display["highlighter_tk"])
        
        # Recalculate center position for images
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        display["canvas"].coords("meter", center_x, center_y)
        display["canvas"].coords("ship", center_x, center_y)
        display["canvas"].coords("highlighter", center_x, center_y)
        
        # Update angle label font size
        new_angle_font_size = max(12, int(window_width / 20))
        display["angle_label"].configure(font=("Helvetica", new_angle_font_size, "bold"))

    def process_hex_data(self, hex_string):
        """Process hex string with proper handling of negative angles."""
        try:
            bytes_data = hex_string.strip().split()
            
            if len(bytes_data) != 32:
                return None, None
                
            if bytes_data[0] != '5A' or bytes_data[1] != 'A5' or bytes_data[-1] != 'AA':
                return None, None
            
            s = sum(int(i,16) for i in bytes_data[2:30])
            
            if int(bytes_data[-2],16) == s%256:
                check_status = "checksum verification successful"
            else:
                check_status = "checksum verification failed"

            roll_high = int(bytes_data[8], 16)
            roll_low = int(bytes_data[9], 16)
            roll_raw = (roll_high << 8) | roll_low
            
            pitch_high = int(bytes_data[10], 16)
            pitch_low = int(bytes_data[11], 16)
            pitch_raw = (pitch_high << 8) | pitch_low
            
            if roll_raw & 0x8000:
                roll_raw = -((~roll_raw & 0xFFFF) + 1)
            if pitch_raw & 0x8000:
                pitch_raw = -((~pitch_raw & 0xFFFF) + 1)
            
            roll_angle = roll_raw / self.RESOLUTION_FACTOR
            pitch_angle = pitch_raw / self.RESOLUTION_FACTOR
            
            roll_angle = round(max(min(roll_angle, self.MAX_ANGLE), self.MIN_ANGLE),1)
            pitch_angle = round(max(min(pitch_angle, self.MAX_ANGLE), self.MIN_ANGLE),1)
            
            return roll_angle, pitch_angle, check_status
            
        except Exception as e:
            print(f"Processing error: {e}")
            return None, None

    def read_serial(self):
        """Read and process serial data."""
        while self.running:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode().strip()
                    if line:
                        hex_data = line.replace("Data Packet:", "").strip()
                        roll, pitch, check_status = self.process_hex_data(hex_data)
    
                        if roll is not None and pitch is not None:
                            self.tilt_angle_1 = roll
                            self.tilt_angle_2 = pitch
                            self.console_queue.put((hex_data, roll, pitch, check_status))
                            
            except Exception as e:
                print(f"Serial read error: {e}")

    def update_display(self):
        """Update the visual display with responsiveness."""
        for display, angle in [(self.ship1_display, self.tilt_angle_1), 
                            (self.ship2_display, self.tilt_angle_2)]:
            # Get the current canvas dimensions
            canvas_width = display["canvas"].winfo_width()
            canvas_height = display["canvas"].winfo_height()

            # Determine the font size dynamically based on the canvas width
            new_font_size = max(12, int(canvas_width / 10))
            display["angle_label"].configure(font=("Helvetica", new_font_size, "bold"))

            # Update angle label text and color
            color = self.get_angle_color(angle)
            display_angle = abs(angle)  # Display absolute value for negative angles
            display["angle_label"].configure(text=f"{display_angle}°", text_color=color)

            # Rotate and resize ship images dynamically
            center_x, center_y = display["center"]

            # Resize and rotate the ship image
            resized_ship = display["ship_img"].resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            rotated_ship = resized_ship.rotate(-angle, resample=Image.BILINEAR, expand=False)
            display["ship_tk"] = ImageTk.PhotoImage(rotated_ship)

            # Resize and rotate the highlighter image
            resized_highlighter = display["highlighter_img"].resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            rotated_highlighter = resized_highlighter.rotate(-angle, resample=Image.BILINEAR, expand=False)
            display["highlighter_tk"] = ImageTk.PhotoImage(rotated_highlighter)

            # Update the canvas items with the new images
            display["canvas"].itemconfig(display["ship_canvas_obj"], image=display["ship_tk"])
            display["canvas"].itemconfig(display["highlighter_canvas_obj"], image=display["highlighter_tk"])

            # Recalculate the center position for the images
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            display["canvas"].coords(display["ship_canvas_obj"], center_x, center_y)
            display["canvas"].coords(display["highlighter_canvas_obj"], center_x, center_y)

        # Schedule the next update
        self.root.after(16, self.update_display)

    def on_close(self):
        self.running = False
        self.console_queue.put((None, None, None))  # Signal console thread to exit
        self.serial_port.close()
        self.root.destroy()

    def start_console_thread(self):
        """Start the console update thread."""
        self.console_thread = threading.Thread(target=self.console_update_thread, daemon=True)
        self.console_thread.start()

    def console_update_thread(self):
        """Thread to clear and update the console periodically."""
        while True:
            try:
                item = self.console_queue.get()
                if item[0] is None:  # Exit signal
                    break

                hex_data, roll, pitch, check_status = item
                current_time = time.time()
                if current_time - self.last_console_update >= self.console_update_interval:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"Hex: {hex_data}")
                    print(f"Status: {check_status}")
                    print(f"Roll: {roll}")
                    print(f"Pitch: {pitch}")
                    self.last_console_update = current_time
            except Exception as e:
                print(f"Console update thread error: {e}")
                break
    
if __name__ == "__main__":
    # Authenticate device before proceeding
    authenticate_device(ALLOWED_SERIAL_NUMBER)
    ctk.set_appearance_mode("dark")  # Set dark mode
    ctk.set_default_color_theme("blue")  # Set green theme
    root = ctk.CTk()
    app = ShipTiltDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
