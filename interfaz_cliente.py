# ============================================================
# RESERVA FÁCIL — Interfaz de usuario final
# python interfaz_cliente.py
# ============================================================
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import tkinter as tk
from tkinter import ttk, messagebox
from abc import ABC, abstractmethod
from datetime import datetime
import re
import os

# ═══════════════════════════════════════════════════════════
# LÓGICA DE NEGOCIO
# ═══════════════════════════════════════════════════════════
LOG_FILE = "reservafacil.log"

def _log(nivel: str, msg: str):
    try:
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{nivel:<8}] {ts} | {msg}\n")
    except OSError:
        pass

class ErrorSistema(Exception):
    def __init__(self, msg, codigo="E000"):
        super().__init__(msg)
        self.codigo = codigo
        _log("ERROR", f"[{codigo}] {msg}")

class DatoInvalidoError(ErrorSistema):
    def __init__(self, campo, detalle=""):
        super().__init__(f"Dato inválido en '{campo}'" + (f": {detalle}" if detalle else ""), "E001")
        self.campo = campo

class ServicioNoDisponibleError(ErrorSistema):
    def __init__(self, nombre):
        super().__init__(f"Servicio no disponible: '{nombre}'", "E003")

class ReservaInvalidaError(ErrorSistema):
    def __init__(self, motivo):
        super().__init__(f"Reserva inválida: {motivo}", "E004")

class OperacionNoPermitidaError(ErrorSistema):
    def __init__(self, op, estado):
        super().__init__(f"No se puede '{op}' desde estado '{estado}'", "E005")

class CalculoInconsistenteError(ErrorSistema):
    def __init__(self, detalle):
        super().__init__(f"Error en cálculo: {detalle}", "E006")

# Validador
_RE_CORREO = re.compile(r"^[\w\.\-]+@[\w\.\-]+\.\w{2,}$")
_RE_DOC    = re.compile(r"^\d{7,12}$")

def validar_cliente_datos(nombre, documento, correo):
    errores = []
    n = str(nombre).strip()
    if not n:          errores.append("El nombre no puede estar vacío.")
    elif len(n) < 3:   errores.append("El nombre debe tener al menos 3 caracteres.")
    elif len(n) > 100: errores.append("El nombre es demasiado largo.")
    if not _RE_DOC.match(str(documento)):
        errores.append("El documento debe tener entre 7 y 12 dígitos numéricos.")
    if not _RE_CORREO.match(str(correo)):
        errores.append("El correo electrónico no es válido.")
    return errores

class Entidad(ABC):
    def __init__(self, id: int):
        if not isinstance(id, int) or id <= 0:
            raise DatoInvalidoError("id", id)
        self._id = id
    def get_id(self): return self._id
    @abstractmethod
    def describir(self) -> str: pass

class Cliente(Entidad):
    _lista: list = []
    _contador = 0

    def __init__(self, nombre: str, documento: str, correo: str):
        Cliente._contador += 1
        super().__init__(Cliente._contador)
        errores = validar_cliente_datos(nombre, documento, correo)
        if errores:
            Cliente._contador -= 1
            raise DatoInvalidoError("formulario", " | ".join(errores))
        self.__nombre    = str(nombre).strip()
        self.__documento = str(documento).strip()
        self.__correo    = str(correo).strip().lower()
        self.__fecha_reg = datetime.now().strftime("%d/%m/%Y")
        Cliente._lista.append(self)
        _log("INFO", f"Cliente registrado: #{self._id} {self.__nombre}")

    def get_nombre(self)    -> str: return self.__nombre
    def get_documento(self) -> str: return self.__documento
    def get_correo(self)    -> str: return self.__correo
    def get_fecha(self)     -> str: return self.__fecha_reg
    def describir(self)     -> str: return f"{self.__nombre} ({self.__documento})"

    @classmethod
    def todos(cls) -> list:    return list(cls._lista)
    @classmethod
    def total(cls) -> int:     return len(cls._lista)
    @classmethod
    def buscar(cls, id: int):
        return next((c for c in cls._lista if c.get_id() == id), None)

class Servicio(Entidad, ABC):
    def __init__(self, id, nombre, precio_base, descripcion, disponible=True):
        super().__init__(id)
        self.__nombre      = nombre
        self.__precio_base = float(precio_base)
        self.__descripcion = descripcion
        self.__disponible  = disponible

    def get_nombre(self)       -> str:   return self.__nombre
    def get_precio_base(self)  -> float: return self.__precio_base
    def get_descripcion(self)  -> str:   return self.__descripcion
    def esta_disponible(self)  -> bool:  return self.__disponible
    def set_disponibilidad(self, v: bool): self.__disponible = v

    @abstractmethod
    def calcular_costo(self, duracion: int) -> float: pass
    @abstractmethod
    def tipo(self) -> str: pass
    def describir(self) -> str: return f"{self.__nombre} (${self.__precio_base:,.0f}/hr)"

class ReservaSala(Servicio):
    ICONO = "🏛"
    def calcular_costo(self, d): return self.get_precio_base() * d * 1.10
    def tipo(self): return "Sala de reuniones"

class AlquilerEquipo(Servicio):
    ICONO = "💻"
    def calcular_costo(self, d): return self.get_precio_base() * d * 0.95
    def tipo(self): return "Alquiler de equipo"

class Asesoria(Servicio):
    ICONO = "👨‍💼"
    def calcular_costo(self, d): return self.get_precio_base() * d * 1.50
    def tipo(self): return "Asesoría profesional"

class Reserva(Entidad):
    _lista:    list = []
    _contador: int  = 0

    TRANS = {
        "pendiente":  {"confirmar", "cancelar"},
        "confirmada": {"cancelar",  "finalizar"},
        "cancelada":  set(),
        "finalizada": set(),
    }
    ESTADO_LABEL = {
        "pendiente":  "Pendiente",
        "confirmada": "Confirmada",
        "cancelada":  "Cancelada",
        "finalizada": "Finalizada",
    }

    def __init__(self, cliente: Cliente, servicio: Servicio, duracion: int):
        Reserva._contador += 1
        super().__init__(Reserva._contador)
        if not isinstance(cliente, Cliente):
            raise DatoInvalidoError("cliente")
        if not isinstance(servicio, Servicio):
            raise DatoInvalidoError("servicio")
        if not isinstance(duracion, int) or duracion < 1 or duracion > 24:
            raise ReservaInvalidaError("La duración debe ser entre 1 y 24 horas.")
        if not servicio.esta_disponible():
            raise ServicioNoDisponibleError(servicio.get_nombre())
        self.__cliente  = cliente
        self.__servicio = servicio
        self.__duracion = duracion
        self.__estado   = "pendiente"
        self.__fecha    = datetime.now()
        self.__codigo   = f"RES-{self._id:04d}"
        Reserva._lista.append(self)
        _log("INFO", f"Reserva creada: {self.__codigo} | {cliente.get_nombre()} | {servicio.get_nombre()}")

    def _check(self, op):
        if op not in self.TRANS.get(self.__estado, set()):
            raise OperacionNoPermitidaError(op, self.__estado)

    def confirmar(self):
        try:
            self._check("confirmar")
            self.__estado = "confirmada"
            _log("INFO", f"Confirmada: {self.__codigo}")
            return True
        finally:
            _log("INFO", f"[finally] confirmar() — {self.__codigo} estado={self.__estado}")

    def cancelar(self, motivo="—"):
        try:
            self._check("cancelar")
            self.__estado = "cancelada"
            self.__servicio.set_disponibilidad(True)
            _log("INFO", f"Cancelada: {self.__codigo} | {motivo}")
            return True
        except OperacionNoPermitidaError:
            raise
        finally:
            _log("INFO", f"[finally] cancelar() — {self.__codigo} estado={self.__estado}")

    def finalizar(self):
        self._check("finalizar")
        self.__estado = "finalizada"
        self.__servicio.set_disponibilidad(True)
        _log("INFO", f"Finalizada: {self.__codigo}")
        return True

    def calcular_total(self, tasa=0.0, descuento=0.0) -> float:
        base = self.__servicio.calcular_costo(self.__duracion)
        if not (0 <= tasa <= 1):
            raise CalculoInconsistenteError("Tasa de impuesto inválida.")
        if descuento < 0 or descuento > base:
            raise CalculoInconsistenteError("Descuento inválido.")
        return max(0.0, base * (1 + tasa) - descuento)

    def get_codigo(self)   -> str:      return self.__codigo
    def get_estado(self)   -> str:      return self.__estado
    def get_cliente(self)  -> Cliente:  return self.__cliente
    def get_servicio(self) -> Servicio: return self.__servicio
    def get_duracion(self) -> int:      return self.__duracion
    def get_fecha(self)    -> str:      return self.__fecha.strftime("%d/%m/%Y %H:%M")
    def describir(self)    -> str:
        return f"{self.__codigo} | {self.__cliente.get_nombre()} | {self.__servicio.get_nombre()}"

    @classmethod
    def todas(cls) -> list:  return list(cls._lista)
    @classmethod
    def total(cls) -> int:   return len(cls._lista)
    @classmethod
    def buscar(cls, id: int):
        return next((r for r in cls._lista if r.get_id() == id), None)


# ── Datos iniciales de servicios ─────────────────────────────
SERVICIOS_DISPONIBLES = [
    ReservaSala(1,    "Sala Ejecutiva A",    60_000, "Capacidad 10 personas. Proyector, pizarra y café incluido.", True),
    ReservaSala(2,    "Sala de Conferencias",90_000, "Capacidad 30 personas. Sistema de videoconferencia.", True),
    AlquilerEquipo(3, "Laptop HP ProBook",   25_000, "Intel i7, 16GB RAM, SSD 512GB. Office incluido.", True),
    AlquilerEquipo(4, "Proyector 4K",        18_000, "3000 lúmenes, HDMI/USB-C, pantalla incluida.", True),
    Asesoria(5,       "Asesoría Jurídica",  150_000, "Consulta legal empresarial con abogado especialista.", True),
    Asesoria(6,       "Asesoría Contable",  120_000, "Revisión de estados financieros y declaraciones.", True),
]

def get_servicio(id: int):
    return next((s for s in SERVICIOS_DISPONIBLES if s.get_id() == id), None)


# ═══════════════════════════════════════════════════════════
# PALETA Y ESTILOS
# ═══════════════════════════════════════════════════════════
C = {
    "bg":         "#F0F4F8",
    "white":      "#FFFFFF",
    "nav":        "#1E3A5F",
    "nav_text":   "#FFFFFF",
    "nav_hover":  "#2A5298",
    "primary":    "#2563EB",
    "primary_dk": "#1D4ED8",
    "success":    "#16A34A",
    "success_bg": "#DCFCE7",
    "error":      "#DC2626",
    "error_bg":   "#FEE2E2",
    "warn":       "#D97706",
    "warn_bg":    "#FEF3C7",
    "info":       "#0369A1",
    "info_bg":    "#E0F2FE",
    "text":       "#1E293B",
    "muted":      "#64748B",
    "border":     "#CBD5E1",
    "card":       "#FFFFFF",
    "card_hover": "#F8FAFC",
    "badge_p":    "#EFF6FF",
    "badge_p_t":  "#1D4ED8",
    "badge_c":    "#DCFCE7",
    "badge_c_t":  "#15803D",
    "badge_x":    "#FEE2E2",
    "badge_x_t":  "#B91C1C",
    "badge_f":    "#F3F4F6",
    "badge_f_t":  "#374151",
}

FONT_TITLE  = ("Segoe UI", 18, "bold")
FONT_H2     = ("Segoe UI", 13, "bold")
FONT_H3     = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")
FONT_MONO   = ("Consolas", 10)

BADGE_COLORS = {
    "pendiente":  (C["badge_p"],  C["badge_p_t"]),
    "confirmada": (C["badge_c"],  C["badge_c_t"]),
    "cancelada":  (C["badge_x"],  C["badge_x_t"]),
    "finalizada": (C["badge_f"],  C["badge_f_t"]),
}


# ═══════════════════════════════════════════════════════════
# WIDGETS REUTILIZABLES
# ═══════════════════════════════════════════════════════════

def make_btn(parent, text, command, style="primary", width=18, pady=8):
    colors = {
        "primary": (C["primary"],    C["primary_dk"], C["white"]),
        "success": (C["success"],    "#15803D",        C["white"]),
        "danger":  (C["error"],      "#B91C1C",        C["white"]),
        "outline": (C["white"],      C["bg"],          C["primary"]),
        "muted":   (C["bg"],         C["border"],      C["muted"]),
    }
    bg, hv, fg = colors.get(style, colors["primary"])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hv, activeforeground=fg,
        relief="flat", font=FONT_BTN, width=width, pady=pady,
        cursor="hand2", bd=0,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=hv))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn

def make_entry(parent, placeholder="", show=""):
    frame = tk.Frame(parent, bg=C["border"], bd=0)
    entry = tk.Entry(
        frame, font=FONT_BODY, relief="flat",
        bg=C["white"], fg=C["text"],
        insertbackground=C["primary"],
        show=show,
    )
    entry.pack(fill="x", padx=1, pady=1, ipady=8, ipadx=10)

    # Placeholder
    if placeholder:
        entry.insert(0, placeholder)
        entry.config(fg=C["muted"])
        def on_focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.config(fg=C["text"])
        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(fg=C["muted"])
        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry._placeholder = placeholder
    else:
        entry._placeholder = ""

    return frame, entry

def get_entry_val(entry):
    v = entry.get().strip()
    return "" if v == getattr(entry, "_placeholder", "") else v

def make_label(parent, text, font=FONT_BODY, color=None, anchor="w", **kw):
    return tk.Label(parent, text=text, font=font,
                    fg=color or C["text"], bg=parent["bg"],
                    anchor=anchor, **kw)

def make_card(parent, padx=20, pady=20):
    outer = tk.Frame(parent, bg=C["border"], bd=0)
    inner = tk.Frame(outer, bg=C["card"])
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    return outer, inner

def notif_show(label_widget, msg, tipo="success"):
    colors = {
        "success": (C["success_bg"], C["success"]),
        "error":   (C["error_bg"],   C["error"]),
        "warn":    (C["warn_bg"],    C["warn"]),
        "info":    (C["info_bg"],    C["info"]),
    }
    bg, fg = colors.get(tipo, colors["info"])
    label_widget.config(text=f"  {msg}", bg=bg, fg=fg)
    label_widget.after(4000, lambda: label_widget.config(text="", bg=C["bg"]))


# ═══════════════════════════════════════════════════════════
# PÁGINAS
# ═══════════════════════════════════════════════════════════

class PageBase(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app

    def on_show(self):
        pass


class PageDashboard(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        # Hero
        hero = tk.Frame(self, bg=C["nav"], pady=40)
        hero.pack(fill="x")
        make_label(hero, "Bienvenido a ReservaFácil",
                   font=("Segoe UI", 22, "bold"), color=C["white"]).pack()
        make_label(hero, "Reserva salas, equipos y asesorías de forma rápida y sencilla.",
                   font=FONT_BODY, color="#93C5FD").pack(pady=(6, 0))

        # Acciones rápidas
        acc = tk.Frame(self, bg=C["bg"], pady=28)
        acc.pack()
        make_label(acc, "¿Qué deseas hacer hoy?",
                   font=FONT_H2, color=C["text"]).pack(pady=(0, 18))

        btns = tk.Frame(acc, bg=C["bg"])
        btns.pack()

        acciones = [
            ("➕  Registrarme",       "Crea tu perfil de cliente",            lambda: self.app.show("clientes"),  "primary"),
            ("📅  Hacer una reserva", "Reserva un servicio al instante",      lambda: self.app.show("nueva_res"), "success"),
            ("📋  Mis reservas",      "Consulta y gestiona tus reservas",     lambda: self.app.show("reservas"),  "outline"),
            ("🛎  Ver servicios",     "Conoce lo que tenemos disponible",     lambda: self.app.show("servicios"), "muted"),
        ]
        for i, (titulo, sub, cmd, estilo) in enumerate(acciones):
            c_outer, c_inner = make_card(btns)
            c_outer.grid(row=0, column=i, padx=10, pady=4, sticky="nsew")
            c_inner.config(padx=24, pady=22, width=185)
            make_label(c_inner, titulo, font=FONT_H3).pack(anchor="w")
            make_label(c_inner, sub, font=FONT_SMALL, color=C["muted"]).pack(anchor="w", pady=(4, 12))
            make_btn(c_inner, "Ir →", cmd, style=estilo, width=12, pady=6).pack(anchor="w")

        # Estadísticas
        self._stats_frame = tk.Frame(self, bg=C["bg"])
        self._stats_frame.pack(pady=10)

    def on_show(self):
        for w in self._stats_frame.winfo_children():
            w.destroy()
        make_label(self._stats_frame, "Estado actual del sistema",
                   font=FONT_H3, color=C["muted"]).pack(pady=(0, 10))
        stats = tk.Frame(self._stats_frame, bg=C["bg"])
        stats.pack()
        datos = [
            ("👤 Clientes",          str(Cliente.total()),  C["primary"]),
            ("🛎 Servicios activos", str(sum(1 for s in SERVICIOS_DISPONIBLES if s.esta_disponible())), C["success"]),
            ("📅 Reservas totales",  str(Reserva.total()),  C["warn"]),
        ]
        for label, valor, color in datos:
            c_o, c_i = make_card(stats)
            c_o.pack(side="left", padx=10)
            c_i.config(padx=30, pady=16)
            make_label(c_i, valor, font=("Segoe UI", 26, "bold"), color=color).pack()
            make_label(c_i, label, font=FONT_SMALL, color=C["muted"]).pack()


class PageClientes(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["bg"], pady=24)
        hdr.pack(fill="x", padx=40)
        make_label(hdr, "Registro de clientes", font=FONT_TITLE).pack(side="left")

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=40, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)

        # Formulario
        f_o, f_i = make_card(body)
        f_o.grid(row=0, column=0, sticky="new", padx=(0, 16))
        f_i.config(padx=24, pady=24)

        make_label(f_i, "Nuevo cliente", font=FONT_H2).pack(anchor="w", pady=(0, 18))

        self._entries = {}
        campos = [
            ("nombre",    "Nombre completo",       "Ej: Laura González"),
            ("documento", "Número de documento",   "Ej: 1234567890"),
            ("correo",    "Correo electrónico",    "Ej: laura@correo.com"),
        ]
        for key, label, ph in campos:
            make_label(f_i, label, font=FONT_SMALL, color=C["muted"]).pack(anchor="w", pady=(8, 2))
            frm, ent = make_entry(f_i, ph)
            frm.pack(fill="x")
            self._entries[key] = ent

        self._notif_form = tk.Label(f_i, text="", font=FONT_SMALL, bg=C["bg"], anchor="w")
        self._notif_form.pack(fill="x", pady=(12, 0))

        make_btn(f_i, "Registrar cliente", self._registrar, "primary", width=22).pack(pady=(6, 0))
        make_btn(f_i, "Limpiar", self._limpiar, "muted", width=22, pady=6).pack(pady=(6, 0))

        # Lista
        l_o, l_i = make_card(body)
        l_o.grid(row=0, column=1, sticky="nsew")
        l_i.config(padx=20, pady=20)

        make_label(l_i, "Clientes registrados", font=FONT_H2).pack(anchor="w", pady=(0, 12))

        cols = ("ID", "Nombre", "Documento", "Correo", "Fecha")
        self._tree = ttk.Treeview(l_i, columns=cols, show="headings", height=14)
        widths = [45, 180, 110, 200, 90]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="center" if col == "ID" else "w")
        sb = ttk.Scrollbar(l_i, orient="vertical", command=self._tree.yview)
        self._tree.config(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _registrar(self):
        nombre   = get_entry_val(self._entries["nombre"])
        documento = get_entry_val(self._entries["documento"])
        correo   = get_entry_val(self._entries["correo"])

        errores = validar_cliente_datos(nombre, documento, correo)
        if errores:
            notif_show(self._notif_form, errores[0], "error")
            return
        try:
            c = Cliente(nombre, documento, correo)
            self._limpiar()
            notif_show(self._notif_form, f"¡Cliente '{c.get_nombre()}' registrado correctamente!", "success")
            self._refresh_tabla()
            self.app.refresh_nav()
        except DatoInvalidoError as e:
            notif_show(self._notif_form, str(e), "error")
        except ErrorSistema as e:
            notif_show(self._notif_form, str(e), "error")

    def _limpiar(self):
        for key, ent in self._entries.items():
            ent.delete(0, "end")
            labels = {"nombre": "Ej: Laura González", "documento": "Ej: 1234567890", "correo": "Ej: laura@correo.com"}
            ent.insert(0, labels[key])
            ent.config(fg=C["muted"])
            ent._placeholder = labels[key]

    def _refresh_tabla(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for c in Cliente.todos():
            self._tree.insert("", "end", values=(
                c.get_id(), c.get_nombre(), c.get_documento(), c.get_correo(), c.get_fecha()
            ))

    def on_show(self):
        self._refresh_tabla()


class PageServicios(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["bg"], pady=24)
        hdr.pack(fill="x", padx=40)
        make_label(hdr, "Catálogo de servicios", font=FONT_TITLE).pack(side="left")

        self._grid = tk.Frame(self, bg=C["bg"])
        self._grid.pack(fill="both", expand=True, padx=40, pady=10)

    def on_show(self):
        for w in self._grid.winfo_children():
            w.destroy()
        iconos = {ReservaSala: "🏛", AlquilerEquipo: "💻", Asesoria: "👨‍💼"}
        for i, s in enumerate(SERVICIOS_DISPONIBLES):
            row, col = divmod(i, 3)
            c_o, c_i = make_card(self._grid)
            c_o.grid(row=row, column=col, padx=12, pady=10, sticky="nsew")
            self._grid.columnconfigure(col, weight=1)
            c_i.config(padx=22, pady=22)

            icono = iconos.get(type(s), "📦")
            disponible = s.esta_disponible()

            # Badge disponibilidad
            badge_bg = C["success_bg"] if disponible else C["error_bg"]
            badge_fg = C["success"]    if disponible else C["error"]
            badge_txt = "Disponible" if disponible else "No disponible"
            tk.Label(c_i, text=badge_txt, bg=badge_bg, fg=badge_fg,
                     font=FONT_SMALL, padx=8, pady=2).pack(anchor="e")

            make_label(c_i, f"{icono}  {s.get_nombre()}", font=FONT_H3).pack(anchor="w", pady=(4, 2))
            make_label(c_i, s.tipo(), font=FONT_SMALL, color=C["muted"]).pack(anchor="w")
            tk.Frame(c_i, bg=C["border"], height=1).pack(fill="x", pady=10)
            make_label(c_i, s.get_descripcion(), font=FONT_SMALL, color=C["muted"],
                       wraplength=210).pack(anchor="w")
            tk.Frame(c_i, bg=C["border"], height=1).pack(fill="x", pady=10)

            make_label(c_i, f"${s.get_precio_base():,.0f} / hora",
                       font=("Segoe UI", 13, "bold"), color=C["primary"]).pack(anchor="w")
            costo_2h = s.calcular_costo(2)
            make_label(c_i, f"2 horas ≈ ${costo_2h:,.0f} (tarifa incluida)",
                       font=FONT_SMALL, color=C["muted"]).pack(anchor="w", pady=(2, 8))

            if disponible:
                make_btn(c_i, "Reservar ahora →",
                         lambda sid=s.get_id(): self._reservar(sid),
                         "primary", width=18, pady=6).pack(anchor="w")

    def _reservar(self, servicio_id):
        self.app.show("nueva_res", servicio_id=servicio_id)


class PageNuevaReserva(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._paso      = 1
        self._cliente   = None
        self._servicio  = None
        self._duracion  = tk.IntVar(value=2)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["bg"], pady=24)
        hdr.pack(fill="x", padx=40)
        make_label(hdr, "Nueva reserva", font=FONT_TITLE).pack(side="left")

        # Indicador de pasos
        self._steps_frame = tk.Frame(self, bg=C["bg"])
        self._steps_frame.pack(pady=(0, 14))

        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(fill="both", expand=True, padx=40)

        self._notif = tk.Label(self, text="", font=FONT_SMALL, bg=C["bg"], anchor="w", padx=40, pady=4)
        self._notif.pack(fill="x")

    def on_show(self, servicio_id=None):
        self._cliente  = None
        self._servicio = None
        self._duracion.set(2)
        if servicio_id:
            s = get_servicio(servicio_id)
            if s and s.esta_disponible():
                self._servicio = s
                self._paso = 1
                self._render_paso1(preselect_servicio=True)
                return
        self._paso = 1
        self._render_paso1()

    def _clear_content(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _render_steps(self, activo):
        for w in self._steps_frame.winfo_children():
            w.destroy()
        pasos = ["1  Cliente", "2  Servicio", "3  Duración", "4  Confirmar"]
        for i, nombre in enumerate(pasos, 1):
            color = C["primary"] if i == activo else (C["success"] if i < activo else C["muted"])
            tk.Label(self._steps_frame, text=nombre, font=FONT_SMALL if i != activo else ("Segoe UI", 9, "bold"),
                     fg=color, bg=C["bg"]).pack(side="left", padx=8)
            if i < len(pasos):
                tk.Label(self._steps_frame, text="›", fg=C["border"], bg=C["bg"],
                         font=FONT_BODY).pack(side="left")

    def _render_paso1(self, preselect_servicio=False):
        self._paso = 1
        self._render_steps(1)
        self._clear_content()
        c_o, c_i = make_card(self._content)
        c_o.pack(fill="x", pady=6)
        c_i.config(padx=28, pady=24)

        make_label(c_i, "Paso 1 — Selecciona tu perfil de cliente", font=FONT_H2).pack(anchor="w", pady=(0, 16))

        if not Cliente.todos():
            make_label(c_i, "Aún no hay clientes registrados.", color=C["muted"]).pack(anchor="w")
            make_btn(c_i, "Registrarme ahora", lambda: self.app.show("clientes"), "primary", width=20).pack(anchor="w", pady=10)
            return

        make_label(c_i, "Selecciona tu nombre:", font=FONT_SMALL, color=C["muted"]).pack(anchor="w", pady=(0, 4))

        self._var_cliente = tk.StringVar()
        opciones = [f"#{c.get_id()}  {c.get_nombre()}  ({c.get_documento()})" for c in Cliente.todos()]
        combo = ttk.Combobox(c_i, textvariable=self._var_cliente, values=opciones,
                             state="readonly", font=FONT_BODY, width=42)
        combo.pack(anchor="w", pady=(0, 16), ipady=6)

        btn_row = tk.Frame(c_i, bg=C["card"])
        btn_row.pack(anchor="w")
        make_btn(btn_row, "Continuar →", lambda: self._confirmar_paso1(), "primary", width=16).pack(side="left", padx=(0, 8))
        make_btn(btn_row, "Cancelar",    lambda: self.app.show("dashboard"), "muted", width=12).pack(side="left")

        if preselect_servicio and opciones:
            combo.current(0)

    def _confirmar_paso1(self):
        val = self._var_cliente.get()
        if not val:
            notif_show(self._notif, "Por favor selecciona un cliente.", "error")
            return
        id_c = int(val.split("#")[1].split(" ")[0])
        self._cliente = Cliente.buscar(id_c)
        self._render_paso2()

    def _render_paso2(self):
        self._paso = 2
        self._render_steps(2)
        self._clear_content()
        c_o, c_i = make_card(self._content)
        c_o.pack(fill="x", pady=6)
        c_i.config(padx=28, pady=24)

        make_label(c_i, "Paso 2 — Elige el servicio", font=FONT_H2).pack(anchor="w", pady=(0, 16))

        if self._servicio:
            # Ya viene preseleccionado desde catálogo
            self._render_servicio_preview(c_i, self._servicio)
            btn_row = tk.Frame(c_i, bg=C["card"])
            btn_row.pack(anchor="w", pady=(12, 0))
            make_btn(btn_row, "Continuar →", self._render_paso3, "primary", width=16).pack(side="left", padx=(0, 8))
            make_btn(btn_row, "Elegir otro", lambda: self._limpiar_servicio_y_render(), "outline", width=14).pack(side="left")
            return

        disponibles = [s for s in SERVICIOS_DISPONIBLES if s.esta_disponible()]
        if not disponibles:
            make_label(c_i, "No hay servicios disponibles en este momento.", color=C["muted"]).pack(anchor="w")
            return

        make_label(c_i, "Selecciona un servicio:", font=FONT_SMALL, color=C["muted"]).pack(anchor="w", pady=(0, 4))
        self._var_serv = tk.StringVar()
        opciones = [f"#{s.get_id()}  {s.get_nombre()}  —  ${s.get_precio_base():,.0f}/hr  [{s.tipo()}]"
                    for s in disponibles]
        combo = ttk.Combobox(c_i, textvariable=self._var_serv, values=opciones,
                             state="readonly", font=FONT_BODY, width=55)
        combo.pack(anchor="w", pady=(0, 16), ipady=6)

        btn_row = tk.Frame(c_i, bg=C["card"])
        btn_row.pack(anchor="w")
        make_btn(btn_row, "Continuar →", lambda: self._confirmar_paso2(disponibles), "primary", width=16).pack(side="left", padx=(0, 8))
        make_btn(btn_row, "Atrás",       self._render_paso1, "muted", width=10).pack(side="left")

    def _render_servicio_preview(self, parent, s):
        iconos = {ReservaSala: "🏛", AlquilerEquipo: "💻", Asesoria: "👨‍💼"}
        icono  = iconos.get(type(s), "📦")
        frm = tk.Frame(parent, bg=C["info_bg"], padx=16, pady=12)
        frm.pack(fill="x")
        make_label(frm, f"{icono}  {s.get_nombre()}", font=FONT_H3, color=C["info"]).pack(anchor="w")
        make_label(frm, s.get_descripcion(), font=FONT_SMALL, color=C["info"]).pack(anchor="w", pady=(4, 0))

    def _limpiar_servicio_y_render(self):
        self._servicio = None
        self._render_paso2()

    def _confirmar_paso2(self, disponibles):
        val = self._var_serv.get()
        if not val:
            notif_show(self._notif, "Por favor selecciona un servicio.", "error")
            return
        id_s = int(val.split("#")[1].split(" ")[0])
        self._servicio = next((s for s in disponibles if s.get_id() == id_s), None)
        self._render_paso3()

    def _render_paso3(self):
        self._paso = 3
        self._render_steps(3)
        self._clear_content()
        c_o, c_i = make_card(self._content)
        c_o.pack(fill="x", pady=6)
        c_i.config(padx=28, pady=24)

        make_label(c_i, "Paso 3 — ¿Cuántas horas necesitas?", font=FONT_H2).pack(anchor="w", pady=(0, 16))

        self._render_servicio_preview(c_i, self._servicio)

        row = tk.Frame(c_i, bg=C["card"])
        row.pack(anchor="w", pady=16)
        make_label(row, "Horas:", font=FONT_BODY).pack(side="left", padx=(0, 12))
        for h in range(1, 9):
            b = tk.Radiobutton(row, text=str(h), variable=self._duracion, value=h,
                               font=FONT_BODY, bg=C["card"], fg=C["text"],
                               activebackground=C["card"], selectcolor=C["primary"],
                               cursor="hand2")
            b.pack(side="left", padx=4)
        make_label(row, "(máx. 8 para reserva rápida)", font=FONT_SMALL, color=C["muted"]).pack(side="left", padx=(8, 0))

        self._lbl_precio = make_label(c_i, "", font=("Segoe UI", 13, "bold"), color=C["primary"])
        self._lbl_precio.pack(anchor="w")
        self._duracion.trace_add("write", lambda *_: self._actualizar_precio())
        self._actualizar_precio()

        btn_row = tk.Frame(c_i, bg=C["card"])
        btn_row.pack(anchor="w", pady=(16, 0))
        make_btn(btn_row, "Continuar →", self._render_paso4, "primary", width=16).pack(side="left", padx=(0, 8))
        make_btn(btn_row, "Atrás",       lambda: self._limpiar_servicio_y_render(), "muted", width=10).pack(side="left")

    def _actualizar_precio(self):
        if self._servicio and hasattr(self, "_lbl_precio"):
            try:
                total = self._servicio.calcular_costo(self._duracion.get())
                total_iva = total * 1.19
                self._lbl_precio.config(
                    text=f"Total estimado: ${total:,.0f}  (con 19% IVA: ${total_iva:,.0f})"
                )
            except Exception:
                pass

    def _render_paso4(self):
        self._paso = 4
        self._render_steps(4)
        self._clear_content()
        c_o, c_i = make_card(self._content)
        c_o.pack(fill="x", pady=6)
        c_i.config(padx=28, pady=24)

        make_label(c_i, "Paso 4 — Confirma tu reserva", font=FONT_H2).pack(anchor="w", pady=(0, 16))

        # Resumen
        resumen = tk.Frame(c_i, bg=C["bg"], padx=20, pady=16)
        resumen.pack(fill="x", pady=(0, 16))
        dur   = self._duracion.get()
        base  = self._servicio.calcular_costo(dur)
        iva   = base * 0.19
        total = base + iva

        filas = [
            ("Cliente:",          self._cliente.get_nombre()),
            ("Documento:",        self._cliente.get_documento()),
            ("Servicio:",         self._servicio.get_nombre()),
            ("Tipo:",             self._servicio.tipo()),
            ("Duración:",         f"{dur} hora{'s' if dur > 1 else ''}"),
            ("Subtotal:",         f"${base:,.0f}"),
            ("IVA (19%):",        f"${iva:,.0f}"),
            ("TOTAL A PAGAR:",    f"${total:,.0f}"),
        ]
        for label, valor in filas:
            fila = tk.Frame(resumen, bg=C["bg"])
            fila.pack(fill="x", pady=2)
            make_label(fila, label, font=("Segoe UI", 10, "bold") if "TOTAL" in label else FONT_SMALL,
                       color=C["muted"]).pack(side="left")
            make_label(fila, valor,
                       font=("Segoe UI", 12, "bold") if "TOTAL" in label else FONT_BODY,
                       color=C["primary"] if "TOTAL" in label else C["text"]).pack(side="right")
            if "TOTAL" in label:
                tk.Frame(resumen, bg=C["border"], height=1).pack(fill="x", pady=(4, 6))

        btn_row = tk.Frame(c_i, bg=C["card"])
        btn_row.pack(anchor="w")
        make_btn(btn_row, "✓  Confirmar reserva", self._confirmar_reserva, "success", width=20).pack(side="left", padx=(0, 10))
        make_btn(btn_row, "Atrás", self._render_paso3, "muted", width=10).pack(side="left")

    def _confirmar_reserva(self):
        try:
            r = Reserva(self._cliente, self._servicio, self._duracion.get())
            r.confirmar()
            self.app.show("exito_reserva", reserva=r)
            self.app.refresh_nav()
        except ServicioNoDisponibleError:
            notif_show(self._notif, "El servicio ya no está disponible. Por favor elige otro.", "error")
        except ReservaInvalidaError as e:
            notif_show(self._notif, str(e), "error")
        except ErrorSistema as e:
            notif_show(self._notif, str(e), "error")


class PageExitoReserva(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._reserva = None
        self._build()

    def _build(self):
        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(expand=True, fill="both")

    def on_show(self, reserva=None):
        self._reserva = reserva
        for w in self._content.winfo_children():
            w.destroy()

        box = tk.Frame(self._content, bg=C["bg"])
        box.place(relx=0.5, rely=0.4, anchor="center")

        tk.Label(box, text="✓", font=("Segoe UI", 52), fg=C["success"], bg=C["bg"]).pack()
        make_label(box, "¡Reserva confirmada!", font=("Segoe UI", 20, "bold"), color=C["success"]).pack(pady=(4, 0))

        if reserva:
            dur   = reserva.get_duracion()
            base  = reserva.get_servicio().calcular_costo(dur)
            total = base * 1.19
            make_label(box, f"Código: {reserva.get_codigo()}", font=FONT_H3, color=C["text"]).pack(pady=(12, 2))
            make_label(box, f"{reserva.get_cliente().get_nombre()}  ·  {reserva.get_servicio().get_nombre()}  ·  {dur}h", font=FONT_BODY, color=C["muted"]).pack()
            make_label(box, f"Total pagado: ${total:,.0f}", font=("Segoe UI", 14, "bold"), color=C["primary"]).pack(pady=(10, 0))

        btns = tk.Frame(box, bg=C["bg"])
        btns.pack(pady=(24, 0))
        make_btn(btns, "Ver mis reservas", lambda: self.app.show("reservas"), "primary", width=18).pack(side="left", padx=(0, 10))
        make_btn(btns, "Hacer otra reserva", lambda: self.app.show("nueva_res"), "outline", width=18).pack(side="left")


class PageReservas(PageBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["bg"], pady=24)
        hdr.pack(fill="x", padx=40)
        make_label(hdr, "Mis reservas", font=FONT_TITLE).pack(side="left")
        make_btn(hdr, "+ Nueva reserva", lambda: self.app.show("nueva_res"),
                 "primary", width=16, pady=6).pack(side="right")

        self._notif = tk.Label(self, text="", font=FONT_SMALL, bg=C["bg"], anchor="w", padx=40)
        self._notif.pack(fill="x")

        tbl_frame = tk.Frame(self, bg=C["bg"], padx=40)
        tbl_frame.pack(fill="both", expand=True)

        cols = ("Código", "Cliente", "Servicio", "Duración", "Total (IVA)", "Fecha", "Estado")
        self._tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=15)
        widths = [100, 160, 180, 80, 110, 135, 100]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="center" if col in ("Duración","Total (IVA)","Estado") else "w")

        sb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self._tree.yview)
        self._tree.config(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Acciones
        acc = tk.Frame(self, bg=C["bg"], padx=40, pady=12)
        acc.pack(fill="x")
        make_label(acc, "Acciones sobre la reserva seleccionada:", font=FONT_SMALL, color=C["muted"]).pack(side="left", padx=(0, 16))
        make_btn(acc, "✓ Confirmar", self._accion_confirmar, "success", width=13, pady=6).pack(side="left", padx=4)
        make_btn(acc, "✕ Cancelar",  self._accion_cancelar,  "danger",  width=13, pady=6).pack(side="left", padx=4)
        make_btn(acc, "⬛ Finalizar", self._accion_finalizar, "outline", width=13, pady=6).pack(side="left", padx=4)

    def _refresh(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for r in Reserva.todas():
            dur   = r.get_duracion()
            total = r.get_servicio().calcular_costo(dur) * 1.19
            self._tree.insert("", "end", iid=str(r.get_id()), values=(
                r.get_codigo(),
                r.get_cliente().get_nombre(),
                r.get_servicio().get_nombre(),
                f"{dur}h",
                f"${total:,.0f}",
                r.get_fecha(),
                Reserva.ESTADO_LABEL.get(r.get_estado(), r.get_estado()),
            ), tags=(r.get_estado(),))

        # Colores por estado
        self._tree.tag_configure("pendiente",  foreground=C["badge_p_t"], background=C["badge_p"])
        self._tree.tag_configure("confirmada", foreground=C["badge_c_t"], background=C["badge_c"])
        self._tree.tag_configure("cancelada",  foreground=C["badge_x_t"], background=C["badge_x"])
        self._tree.tag_configure("finalizada", foreground=C["badge_f_t"])

    def _selected_reserva(self):
        sel = self._tree.selection()
        if not sel:
            notif_show(self._notif, "Selecciona una reserva de la tabla primero.", "warn")
            return None
        return Reserva.buscar(int(sel[0]))

    def _accion_confirmar(self):
        r = self._selected_reserva()
        if not r: return
        try:
            r.confirmar()
            notif_show(self._notif, f"Reserva {r.get_codigo()} confirmada.", "success")
            self._refresh()
            self.app.refresh_nav()
        except OperacionNoPermitidaError as e:
            notif_show(self._notif, f"No se puede confirmar: ya está {r.get_estado()}.", "error")
        except ErrorSistema as e:
            notif_show(self._notif, str(e), "error")

    def _accion_cancelar(self):
        r = self._selected_reserva()
        if not r: return
        if not messagebox.askyesno("Cancelar reserva",
                                   f"¿Seguro que deseas cancelar la reserva {r.get_codigo()}?\nEsta acción no se puede deshacer."):
            return
        try:
            r.cancelar("Cancelada por el usuario")
            notif_show(self._notif, f"Reserva {r.get_codigo()} cancelada.", "info")
            self._refresh()
            self.app.refresh_nav()
        except OperacionNoPermitidaError:
            notif_show(self._notif, f"No se puede cancelar: ya está {r.get_estado()}.", "error")
        except ErrorSistema as e:
            notif_show(self._notif, str(e), "error")

    def _accion_finalizar(self):
        r = self._selected_reserva()
        if not r: return
        try:
            r.finalizar()
            notif_show(self._notif, f"Reserva {r.get_codigo()} finalizada.", "success")
            self._refresh()
            self.app.refresh_nav()
        except OperacionNoPermitidaError:
            notif_show(self._notif, f"No se puede finalizar: estado actual es '{r.get_estado()}'.", "error")
        except ErrorSistema as e:
            notif_show(self._notif, str(e), "error")

    def on_show(self):
        self._refresh()


# ═══════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ReservaFácil")
        self.geometry("1200x740")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])

        self._style()
        self._build_nav()
        self._build_pages()
        self.show("dashboard")
        _log("INFO", "Aplicación iniciada")

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview",
                     font=FONT_BODY, rowheight=32,
                     background=C["white"], fieldbackground=C["white"],
                     foreground=C["text"])
        s.configure("Treeview.Heading",
                     font=("Segoe UI", 9, "bold"),
                     background=C["bg"], foreground=C["muted"],
                     relief="flat")
        s.map("Treeview", background=[("selected", C["primary"])],
              foreground=[("selected", C["white"])])
        s.configure("TCombobox", font=FONT_BODY)

    def _build_nav(self):
        nav = tk.Frame(self, bg=C["nav"], height=54)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        # Logo
        tk.Label(nav, text="  ReservaFácil", font=("Segoe UI", 14, "bold"),
                 fg=C["white"], bg=C["nav"]).pack(side="left", padx=12)

        # Links
        self._nav_btns = {}
        links = [
            ("dashboard",  "Inicio"),
            ("servicios",  "Servicios"),
            ("clientes",   "Clientes"),
            ("nueva_res",  "Reservar"),
            ("reservas",   "Mis reservas"),
        ]
        for key, label in links:
            btn = tk.Button(nav, text=label, bg=C["nav"], fg="#93C5FD",
                            activebackground=C["nav_hover"], activeforeground=C["white"],
                            relief="flat", font=FONT_BODY, padx=14, pady=16,
                            cursor="hand2", bd=0,
                            command=lambda k=key: self.show(k))
            btn.pack(side="left")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["nav_hover"], fg=C["white"]))
            btn.bind("<Leave>", lambda e, b=btn, k2=key: b.config(
                bg=C["nav_hover"] if self._current == k2 else C["nav"],
                fg=C["white"] if self._current == k2 else "#93C5FD"))
            self._nav_btns[key] = btn

        # Contador reservas (badge)
        self._badge = tk.Label(nav, text="", font=FONT_SMALL,
                               bg=C["error"], fg=C["white"], padx=6, pady=2)

        # Stats rápidas en nav
        self._nav_stats = tk.Label(nav, text="", font=FONT_SMALL,
                                   fg="#93C5FD", bg=C["nav"])
        self._nav_stats.pack(side="right", padx=20)

        self._current = "dashboard"

    def _build_pages(self):
        self._container = tk.Frame(self, bg=C["bg"])
        self._container.pack(fill="both", expand=True)

        self._pages: dict[str, PageBase] = {
            "dashboard":   PageDashboard(self._container, self),
            "clientes":    PageClientes(self._container, self),
            "servicios":   PageServicios(self._container, self),
            "nueva_res":   PageNuevaReserva(self._container, self),
            "reservas":    PageReservas(self._container, self),
            "exito_reserva": PageExitoReserva(self._container, self),
        }
        for page in self._pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show(self, page_key: str, **kwargs):
        self._current = page_key
        page = self._pages.get(page_key)
        if page:
            page.tkraise()
            page.on_show(**kwargs)
        self._update_nav_active()
        self.refresh_nav()
        _log("INFO", f"Navegando a: {page_key}")

    def _update_nav_active(self):
        for key, btn in self._nav_btns.items():
            if key == self._current:
                btn.config(bg=C["nav_hover"], fg=C["white"],
                           font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=C["nav"], fg="#93C5FD", font=FONT_BODY)

    def refresh_nav(self):
        c = Cliente.total()
        r = Reserva.total()
        self._nav_stats.config(
            text=f"👤 {c} cliente{'s' if c != 1 else ''}   📅 {r} reserva{'s' if r != 1 else ''}"
        )


# ─── Punto de entrada ─────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
    _log("INFO", "Aplicación cerrada")
