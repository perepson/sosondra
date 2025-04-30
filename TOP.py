import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import Dialog


class EntryDialog(Dialog):

    def __init__(self, parent, title, fields):
        self.fields = fields
        super().__init__(parent, title=title)

    def body(self, master):
        self.entries = {}
        for i, (field, default) in enumerate(self.fields.items()):
            tk.Label(master, text=field).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(master)
            entry.insert(0, default)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[field] = entry
        return master

    def apply(self):
        self.result = {field: entry.get() for field, entry in self.entries.items()}


class DatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Интерфейс для работы с базой данных")
        self.conn = None

        # Верхняя панель (кнопки + поиск)
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill=tk.X, pady=5)

        self.open_db_btn = tk.Button(self.top_frame, text="Выбрать БД", command=self.open_db)
        self.open_db_btn.pack(side=tk.LEFT, padx=5)

        self.search_entry = tk.Entry(self.top_frame)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self.filter_data)

        # Кнопки CRUD
        self.crud_frame = tk.Frame(root)
        self.crud_frame.pack(fill=tk.X, pady=5)

        self.add = tk.Button(self.crud_frame, text="Добавить", command=self.add_inf, state=tk.DISABLED)
        self.add.pack(side=tk.LEFT, padx=5)

        self.edit = tk.Button(self.crud_frame, text="Изменить", command=self.edit_inf, state=tk.DISABLED)
        self.edit.pack(side=tk.LEFT, padx=5)

        self.delete = tk.Button(self.crud_frame, text="Удалить", command=self.delete_inf, state=tk.DISABLED)
        self.delete.pack(side=tk.LEFT, padx=5)

        # Выпадающий список таблиц
        self.table_combo = ttk.Combobox(root, state="readonly")
        self.table_combo.bind("<<ComboboxSelected>>", self.show_data)
        self.table_combo.pack(fill=tk.X, pady=5, padx=5)

        # Таблица для вывода данных
        self.tree_frame = tk.Frame(root)
        self.tree_frame.pack(expand=True, fill=tk.BOTH, pady=5)

        self.tree = ttk.Treeview(self.tree_frame)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def open_db(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Базы данных", "*.db *.sqlite"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                if self.conn:
                    self.conn.close()
                self.conn = sqlite3.connect(file_path)
                self.update_table_list()
                self.add.config(state=tk.NORMAL)
                messagebox.showinfo("Подключение к базе данных", f"Успешное подключение к базе данных: {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def update_table_list(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
        tables = [table[0] for table in cursor.fetchall()]
        self.table_combo['values'] = tables
        if tables:
            self.table_combo.current(0)
            self.show_data()

    def show_data(self, event=None):
        table_name = self.table_combo.get()
        if not table_name:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]

            cursor.execute(f"SELECT * FROM {table_name} LIMIT 500")
            rows = cursor.fetchall()

            self.tree.delete(*self.tree.get_children())
            self.tree['columns'] = columns
            self.tree['show'] = 'headings'

            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=120, stretch=True)

            for row in rows:
                self.tree.insert("", tk.END, values=row)

            self.edit.config(state=tk.NORMAL)
            self.delete.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {str(e)}")

    def filter_data(self, event=None):
        search_term = self.search_entry.get().lower()
        for item in self.tree.get_children():
            values = [str(v).lower() for v in self.tree.item(item)['values']]
            if any(search_term in val for val in values):
                self.tree.item(item, tags=('match',))
                self.tree.selection_set(item)
            else:
                self.tree.item(item, tags=('no_match',))
                self.tree.selection_remove(item)
        self.tree.tag_configure('match', background='')
        self.tree.tag_configure('no_match', background='lightgray')

    def add_inf(self):
        table_name = self.table_combo.get()
        if not table_name:
            return

        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        dialog = EntryDialog(
            self.root,
            f"Добавить запись в {table_name}",
            {col: "" for col in columns}
        )
        if dialog.result:
            try:
                columns_str = ", ".join(dialog.result.keys())
                placeholders = ", ".join(["?"] * len(dialog.result))
                cursor.execute(
                    f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})",
                    list(dialog.result.values())
                )
                self.conn.commit()
                self.show_data()
                messagebox.showinfo("Успех", "Запись добавлена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка добавления: {str(e)}")

    def edit_inf(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запись для редактирования")
            return

        table_name = self.table_combo.get()
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        values = self.tree.item(selected[0])['values']

        dialog = EntryDialog(
            self.root,
            f"Редактировать запись в {table_name}",
            dict(zip(columns, values))
        )

        if dialog.result:
            try:
                set_clause = ", ".join([f"{col} = ?" for col in columns])
                cursor.execute(
                    f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?",
                    list(dialog.result.values()) + [values[0]]
                )
                self.conn.commit()
                self.show_data()
                messagebox.showinfo("Успех", "Запись обновлена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка редактирования: {str(e)}")

    def delete_inf(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запись для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранную запись?"):
            table_name = self.table_combo.get()
            cursor = self.conn.cursor()
            try:
                values = self.tree.item(selected[0])['values']
                cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (values[0],))
                self.conn.commit()
                self.show_data()
                messagebox.showinfo("Успех", "Запись удалена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка удаления: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseApp(root)
    root.geometry("700x500")
    root.mainloop()