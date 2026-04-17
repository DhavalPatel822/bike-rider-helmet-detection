import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from ultralytics import YOLO
import os
from pathlib import Path

class BikeHelmetDetectionGUI:
    """GUI application for bike helmet detection using YOLO model"""
    
    def __init__(self, root):
        """Initialize the GUI application"""
        self.root = root
        self.root.title("Bike Helmet Detection System")
        self.root.geometry("900x700")
        self.root.config(bg="lightgray")
        
        # Initialize model
        self.model = None
        self.current_image = None
        self.current_image_path = None
        self.detection_results = None
        
        # Color mapping for classes
        self.color_map = {
            0: (0, 255, 0),      # Green for "With Helmet"
            1: (255, 0, 0)       # Red for "Without Helmet"
        }
        
        # Create GUI components
        self.create_widgets()
        self.load_model()
    
    def create_widgets(self):
        """Create all GUI components"""
        # Title
        title_label = tk.Label(
            self.root, 
            text="Bike Helmet Detection System", 
            font=("Arial", 18, "bold"),
            bg="lightgray"
        )
        title_label.pack(pady=10)
        
        # Button frame
        button_frame = tk.Frame(self.root, bg="lightgray")
        button_frame.pack(pady=10)
        
        # Load Image button
        load_btn = tk.Button(
            button_frame,
            text="Load Image",
            command=self.load_image,
            width=20,
            bg="blue",
            fg="white",
            font=("Arial", 11)
        )
        load_btn.grid(row=0, column=0, padx=5)
        
        # Detect button
        detect_btn = tk.Button(
            button_frame,
            text="Run Detection",
            command=self.run_detection,
            width=20,
            bg="green",
            fg="white",
            font=("Arial", 11)
        )
        detect_btn.grid(row=0, column=1, padx=5)
        
        # Clear button
        clear_btn = tk.Button(
            button_frame,
            text="Clear Image",
            command=self.clear_image,
            width=20,
            bg="red",
            fg="white",
            font=("Arial", 11)
        )
        clear_btn.grid(row=0, column=2, padx=5)
        
        # Image display label
        self.image_label = tk.Label(self.root, bg="white")
        self.image_label.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Statistics frame
        self.stats_frame = tk.Frame(self.root, bg="lightgray")
        self.stats_frame.pack(pady=10, padx=10, fill=tk.X)
        
        self.stats_label = tk.Label(
            self.stats_frame,
            text="No image loaded",
            font=("Arial", 10),
            bg="lightgray",
            justify=tk.LEFT
        )
        self.stats_label.pack(anchor="w")
    
    def load_model(self):
        """Load the YOLO model"""
        try:
            if os.path.exists("best.pt"):
                self.model = YOLO("best.pt")
                messagebox.showinfo("Success", "Model loaded successfully!")
            else:
                messagebox.showerror("Error", "Model file 'best.pt' not found!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
    
    def load_image(self):
        """Load an image from file dialog"""
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.current_image_path = file_path
                self.current_image = Image.open(file_path)
                
                # Resize image for display (max 800x600)
                self.current_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
                
                # Display image
                self.display_image(self.current_image)
                
                # Update stats
                self.update_stats(f"Image loaded: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def run_detection(self):
        """Run detection on the loaded image"""
        if self.model is None:
            messagebox.showerror("Error", "Model not loaded!")
            return
        
        if self.current_image_path is None:
            messagebox.showerror("Error", "No image loaded!")
            return
        
        try:
            # Run detection on original image
            results = self.model.predict(
                source=self.current_image_path,
                conf=0.5,
                save=False,
                verbose=False
            )
            
            self.detection_results = results[0]
            
            # Create annotated image
            annotated_image = self.draw_detections()
            self.display_image(annotated_image)
            
            # Update statistics
            self.display_statistics()
            
        except Exception as e:
            messagebox.showerror("Error", f"Detection failed: {str(e)}")
    
    def draw_detections(self):
        """Draw bounding boxes on the image"""
        if self.detection_results is None:
            return self.current_image
        
        # Reload original image
        image = Image.open(self.current_image_path)
        image.thumbnail((800, 600), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(image)
        
        boxes = self.detection_results.boxes
        
        # Draw each detection
        for box in boxes:
            # Get coordinates
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Get class and confidence
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = self.detection_results.names[class_id]
            
            # Get color
            color = self.color_map.get(class_id, (255, 255, 255))
            
            # Draw rectangle
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            draw.text((x1, y1 - 10), label, fill=color)
        
        return image
    
    def display_statistics(self):
        """Display detection statistics"""
        if self.detection_results is None:
            return
        
        boxes = self.detection_results.boxes
        total_detections = len(boxes)
        
        # Count by class
        class_counts = {}
        for box in boxes:
            class_id = int(box.cls[0])
            class_name = self.detection_results.names[class_id]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        # Build stats text
        stats_text = f"Total Detections: {total_detections}\n"
        for class_name, count in class_counts.items():
            stats_text += f"{class_name}: {count}\n"
        
        self.update_stats(stats_text)
    
    def display_image(self, image):
        """Display image in the label"""
        # Convert PIL image to PhotoImage
        photo = ImageTk.PhotoImage(image)
        
        # Update label
        self.image_label.config(image=photo)
        self.image_label.image = photo  # Keep a reference
    
    def update_stats(self, text):
        """Update statistics label"""
        self.stats_label.config(text=text)
    
    def clear_image(self):
        """Clear the displayed image"""
        self.image_label.config(image="")
        self.image_label.image = None
        self.current_image = None
        self.current_image_path = None
        self.detection_results = None
        self.update_stats("No image loaded")


def main():
    """Main function to start the application"""
    root = tk.Tk()
    app = BikeHelmetDetectionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
