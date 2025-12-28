import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import json
from typing import List, Dict
import hashlib


class ImageBrowserApp:
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.nef')
    TAG_OUTTAKE = "outtakes"
    TAGS_FILENAME = ".image_tags.json"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Browser")
        self.root.geometry("1000x600")

        self.current_folder = ""
        self.tags: Dict[str, List[str]] = {}
        self.tags_file = ""
        self.programmatic_selection = False
        self.last_idx = -1
        self._setup_ui()
        # Bind specifically to the listbox so it catches the event first
        self.image_listbox.bind('1', self.tag_as_outtake)

    def _setup_ui(self):
        self._create_menu()

        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left Column - Listbox
        self.left_frame = tk.Frame(self.paned_window, width=300)
        self.image_listbox = tk.Listbox(self.left_frame)
        self.image_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.image_listbox, command=self.image_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_listbox.config(yscrollcommand=scrollbar.set)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)

        # Legend
        legend_text = "how to use\n * select folder with images\n * navigate wit arrow keys\n * tag images with key [1]\n * move to OUTTAKES via actions"
        self.legend_label = tk.Label(self.left_frame, text=legend_text, justify=tk.LEFT, 
                                     anchor="w", font=("TkDefaultFont", 8, "italic"),
                                     padx=5, pady=5)
        self.legend_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Right Column - Preview
        self.right_frame = tk.Frame(self.paned_window, bg="gray")
        self.preview_label = tk.Label(self.right_frame, text="Select an image to preview", bg="gray", fg="white")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        self.paned_window.add(self.left_frame, stretch="never")
        self.paned_window.add(self.right_frame, stretch="always")

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        action_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=action_menu)
        action_menu.add_command(label="Move to OUTTAKES", command=self.move_outtakes)

    def open_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.current_folder = folder_path
            self.root.title(f"Image Browser - {self.current_folder}")
            self.tags_file = os.path.join(folder_path, self.TAGS_FILENAME)
            self.load_tags()
            self.load_images()

    def load_tags(self):
        self.tags = {}
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r') as f:
                    self.tags = json.load(f)
            except Exception as e:
                print(f"Error loading tags: {e}")

    def save_tags(self):
        try:
            with open(self.tags_file, 'w') as f:
                json.dump(self.tags, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save tags: {e}")

    def load_images(self):
        self.image_listbox.delete(0, tk.END)
        try:
            files = [f for f in os.listdir(self.current_folder)
                     if f.lower().endswith(self.IMAGE_EXTENSIONS)]
            if not files:
                messagebox.showinfo("No Images", "No supported image files found.")
                return
            for file in files:
                self.image_listbox.insert(tk.END, self.get_display_name(file))
        except Exception as e:
            messagebox.showerror("Error", f"Could not load images: {e}")

    def get_display_name(self, filename: str) -> str:
        if filename in self.tags and self.tags[filename]:
            return f"{filename} [{', '.join(self.tags[filename])}]"
        return filename

    def get_filename_from_display(self, display_name: str) -> str:
        return display_name.split(' [')[0] if '[' in display_name else display_name

    def tag_as_outtake(self, event=None):
        selection = self.image_listbox.curselection()
        if not selection:
            return "break"

        idx = selection[0]
        original_idx = idx # Store the original index to restore focus later
        display_name = self.image_listbox.get(idx)
        filename = self.get_filename_from_display(display_name)
        base_name = os.path.splitext(filename)[0]

        # Find all files in the current list that share this base name
        # this ensures both JPG and NEF get tagged together
        indices_to_update = []
        all_items = self.image_listbox.get(0, tk.END)
        
        target_state_add = True # Determine if we are adding or removing
        if filename in self.tags and self.TAG_OUTTAKE in self.tags[filename]:
            target_state_add = False

        for i, item in enumerate(all_items):
            fname = self.get_filename_from_display(item)
            if os.path.splitext(fname)[0] == base_name:
                file_tags = self.tags.setdefault(fname, [])
                if target_state_add and self.TAG_OUTTAKE not in file_tags:
                    file_tags.append(self.TAG_OUTTAKE)
                elif not target_state_add and self.TAG_OUTTAKE in file_tags:
                    file_tags.remove(self.TAG_OUTTAKE)
                indices_to_update.append((i, fname))

        self.save_tags()
        
        # Update the UI for all affected sister files
        for i, fname in indices_to_update:
            self._update_listbox_item(i, fname)
            
        # Explicitly restore selection and focus to the original image file
        self.programmatic_selection = True
        self.image_listbox.selection_clear(0, tk.END)
        self.image_listbox.selection_set(original_idx)
        self.image_listbox.activate(original_idx)
        self.image_listbox.see(original_idx)
        self.last_idx = original_idx
        self.programmatic_selection = False

        return "break"

    def _update_listbox_item(self, index: int, filename: str):
        self.programmatic_selection = True
        try:
            self.image_listbox.delete(index)
            self.image_listbox.insert(index, self.get_display_name(filename))
            
            # Resync everything: Selection, Active Cursor, and the Anchor
            self.image_listbox.selection_set(index)
            self.image_listbox.activate(index)
            self.image_listbox.selection_anchor(index)
            self.image_listbox.see(index)
        finally:
            self.programmatic_selection = False

    def on_image_select(self, event):
        if self.programmatic_selection:
            return
            
        selection = self.image_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        
        # If we didn't actually move, do nothing
        if idx == self.last_idx:
            return

        filename = self.get_filename_from_display(self.image_listbox.get(idx))
        
        # If it's a NEF file, skip it in the direction we were moving
        if filename.lower().endswith('.nef'):
            direction = 1 if idx > self.last_idx else -1
            next_idx = idx + direction
            
            # Ensure we stay within bounds
            if 0 <= next_idx < self.image_listbox.size():
                self.programmatic_selection = True
                self.image_listbox.selection_clear(0, tk.END)
                self.image_listbox.selection_set(next_idx)
                self.image_listbox.activate(next_idx)
                self.image_listbox.see(next_idx)
                self.programmatic_selection = False
                
                # Recursive call to check if the NEXT one is also a RAW file
                self.on_image_select(None)
                return
            else:
                # If we hit the end of the list, just stay where we were
                self.image_listbox.selection_clear(0, tk.END)
                self.image_listbox.selection_set(self.last_idx)
                return

        self.last_idx = idx
        self.show_preview(os.path.join(self.current_folder, filename))

    def show_preview(self, filepath: str):
        try:
            self.root.update_idletasks()  # Ensure dimensions are updated
            width = max(self.right_frame.winfo_width() - 20, 100)
            height = max(self.right_frame.winfo_height() - 20, 100)
            
            img = Image.open(filepath)
            img.thumbnail((width, height))
            self.tk_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.tk_img, text="")
        except Exception as e:
            self.preview_label.config(image='', text=f"Error: {e}")

    def get_file_hash(self, filepath: str) -> str:
        """Calculate SHA-1 hash of a file."""
        sha1 = hashlib.sha1()
        try:
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(65536)  # Read in 64kb chunks
                    if not data:
                        break
                    sha1.update(data)
            return sha1.hexdigest()
        except Exception:
            return ""

    def move_outtakes(self):
        if not self.current_folder:
            messagebox.showwarning("No Folder", "Please open a folder first.")
            return

        files_to_move = [fname for fname, f_tags in self.tags.items() 
                         if self.TAG_OUTTAKE in f_tags]

        if not files_to_move:
            messagebox.showinfo("No Outtakes", "No images are currently tagged as outtakes.")
            return

        outtakes_dir = os.path.join(self.current_folder, "OUTTAKES")
        
        try:
            if not os.path.exists(outtakes_dir):
                os.makedirs(outtakes_dir)

            processed_count = 0
            hash_matches = 0
            hash_mismatches = 0

            for filename in files_to_move:
                src = os.path.join(self.current_folder, filename)
                dst = os.path.join(outtakes_dir, filename)
                
                if os.path.exists(src):
                    # 1. Generate hash of original
                    before_hash = self.get_file_hash(src)
                    
                    # 2. Copy to destination (preserving metadata)
                    shutil.copy2(src, dst)
                    processed_count += 1
                    
                    # 3. Generate hash of the copy
                    after_hash = self.get_file_hash(dst)
                    
                    # 4. Compare and only delete original if safe
                    if before_hash and before_hash == after_hash:
                        os.remove(src)
                        hash_matches += 1
                    else:
                        hash_mismatches += 1

            # Reset tags and save
            self.tags = {}
            self.save_tags()
            
            # Refresh UI
            self.load_images()
            self.preview_label.config(image='', text="Select an image to preview")
            
            summary = (
                f"Files processed: {processed_count}\n"
                f"Integrity check (SHA-1):\n"
                f"  - Verified & Deleted original: {hash_matches}\n"
                f"  - Mismatches (Original kept): {hash_mismatches}\n\n"
                f"All local tags have been cleared."
            )
            
            if hash_mismatches > 0:
                messagebox.showwarning("Integrity Warning", 
                                     f"Warning: {hash_mismatches} files failed verification. "
                                     f"The originals were NOT deleted for safety.\n\n{summary}")
            else:
                messagebox.showinfo("Operation Complete", summary)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBrowserApp(root)
    root.mainloop()
