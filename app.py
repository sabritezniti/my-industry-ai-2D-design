import streamlit as st
import ezdxf
from ezdxf import bbox
import numpy as np
from PIL import Image
import cv2
import io
import os
import tempfile
from pathlib import Path
import math
import hashlib
import time
import re
from datetime import datetime

# ============================================
# CONFIGURATION & BRANDING
# ============================================
APP_NAME = "My Industry AI 2D Design"
APP_ICON = "🏭"
CONTACT_EMAIL = "postmaster@myindustryai.tn"

# Clé de licence (NE JAMAIS AFFICHER)
_LICENSE_KEY_HASH = "a3f5c8e9d2b1f4e7a6c0d3b8f5e2a1c9"
FREE_REQUESTS_LIMIT = 5

# ============================================
# FONCTIONS DE GESTION DE LICENCE
# ============================================

def _hash_key(key):
    return hashlib.md5(key.encode()).hexdigest()

def verify_license_key(key):
    return _hash_key(key) == _LICENSE_KEY_HASH

def init_session_state():
    defaults = {
        'request_count': 0,
        'license_activated': False,
        'user_email': None,
        'user_name': None,
        'is_logged_in': False,
        'generated_doc': None,
        'generated_svg': None,
        'image_dxf_bytes': None,
        'image_dxf_svg': None,
        'repaired_dxf_bytes': None,
        'repaired_dxf_svg': None,
        'repaired_dxf_repairs': None,
        'last_rect': None,
        'show_license_modal': False,
        'show_login_modal': False,
        'parametric_vars': {},
        'image_trace_data': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_remaining_requests():
    if st.session_state.license_activated:
        return float('inf')
    return max(0, FREE_REQUESTS_LIMIT - st.session_state.request_count)

def can_make_request():
    if st.session_state.license_activated:
        return True
    return st.session_state.request_count < FREE_REQUESTS_LIMIT

def increment_request():
    st.session_state.request_count += 1

# ============================================
# FONCTIONS DE CONNEXION
# ============================================

def simulate_gmail_login():
    st.markdown("""
    <div style="background: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;">
        <h3>🔐 Connexion Gmail</h3>
        <p>Connectez-vous avec votre compte Google</p>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("Email Gmail", placeholder="votre.email@gmail.com", key="gmail_email")
    password = st.text_input("Mot de passe", type="password", placeholder="••••••••", key="gmail_password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔓 Se connecter", use_container_width=True, key="btn_login"):
            if email and "@gmail.com" in email and password:
                st.session_state.is_logged_in = True
                st.session_state.user_email = email
                st.session_state.user_name = email.split("@")[0].replace(".", " ").title()
                st.session_state.show_login_modal = False
                st.success("✅ Connexion réussie!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Email ou mot de passe invalide")
    with col2:
        if st.button("❌ Annuler", use_container_width=True, key="btn_cancel_login"):
            st.session_state.show_login_modal = False
            st.rerun()

def show_license_activation():
    st.markdown("""
    <div style="background: #fff3cd; padding: 20px; border-radius: 10px; border: 2px solid #ffc107;">
        <h3>🔑 Activation de Licence</h3>
        <p>Vous avez atteint la limite de <b>5 requêtes gratuites</b>.</p>
        <p>Contactez <b>""" + CONTACT_EMAIL + """</b> pour obtenir une clé.</p>
    </div>
    """, unsafe_allow_html=True)

    license_input = st.text_input(
        "Entrez votre clé de licence:",
        type="password",
        placeholder="XXXX-XXXX-XXXX-XXXX",
        key="license_input"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Activer", use_container_width=True, key="btn_activate"):
            if license_input and verify_license_key(license_input):
                st.session_state.license_activated = True
                st.session_state.show_license_modal = False
                st.success("🎉 Licence activée! Accès illimité.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Clé invalide. Contactez " + CONTACT_EMAIL)
    with col2:
        if st.button("📧 Contacter", use_container_width=True, key="btn_contact"):
            import webbrowser
            webbrowser.open(f"mailto:{CONTACT_EMAIL}?subject=Demande%20licence%20My%20Industry%20AI")

def show_user_profile():
    if st.session_state.is_logged_in:
        st.markdown(f"""
        <div style="background: #d4edda; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 40px; height: 40px; background: #1f77b4; border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                    {st.session_state.user_name[0] if st.session_state.user_name else "?"}
                </div>
                <div>
                    <div style="font-weight: bold;">{st.session_state.user_name or "Utilisateur"}</div>
                    <div style="font-size: 0.8rem; color: #666;">{st.session_state.user_email or ""}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.license_activated:
            st.markdown("""
            <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;">
                <span style="color: #155724;">✅ Licence active — Illimité</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            remaining = get_remaining_requests()
            color = "#856404" if remaining > 0 else "#721c24"
            bg = "#fff3cd" if remaining > 0 else "#f8d7da"
            st.markdown(f"""
            <div style="background: {bg}; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;">
                <span style="color: {color};">🎁 Requêtes restantes: {remaining} / {FREE_REQUESTS_LIMIT}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚪 Déconnexion", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    else:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 15px;">
            <p>🔒 Connectez-vous pour utiliser l'application</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔐 Se connecter avec Gmail", use_container_width=True, type="primary"):
            st.session_state.show_login_modal = True
            st.rerun()

# ============================================
# PARSER PARAMÉTRIQUE MULTI-OPÉRATIONS
# ============================================

class ParametricParser:
    """Parser avancé supportant variables, multi-opérations, positions relatives"""

    def __init__(self):
        self.variables = {}
        self.entities_created = []
        self.last_rect = None

    def extract_numbers(self, s):
        """Extrait tous les nombres d'une chaîne"""
        return [float(x) for x in re.findall(r"\d+\.?\d*", s)]

    def resolve_value(self, value_str):
        """Résout une valeur (nombre ou variable)"""
        value_str = value_str.strip()

        # Variable
        if value_str.startswith("$"):
            var_name = value_str[1:]
            if var_name in self.variables:
                return self.variables[var_name]
            else:
                raise ValueError(f"Variable '${var_name}' non définie")

        # Expression simple
        if "+" in value_str or "-" in value_str or "*" in value_str or "/" in value_str:
            try:
                for var_name, var_value in self.variables.items():
                    value_str = value_str.replace(f"${var_name}", str(var_value))
                return eval(value_str)
            except:
                pass

        # Nombre simple
        nums = self.extract_numbers(value_str)
        if nums:
            return nums[0]

        return None

    def parse_variables(self, text):
        """Extrait les déclarations de variables"""
        var_pattern = r"\$?(\w+)\s*=\s*([\d\.+-/*$\w]+)"
        matches = re.finditer(var_pattern, text)
        for match in matches:
            var_name = match.group(1)
            var_expr = match.group(2)
            try:
                value = self.resolve_value(var_expr)
                if value is not None:
                    self.variables[var_name] = value
            except:
                pass

    def get_rectangle_bounds(self):
        """Retourne les bounds du dernier rectangle"""
        if self.last_rect:
            return self.last_rect
        return {"x": 0, "y": 0, "width": 100, "height": 100}

    def calculate_position(self, position_desc, shape_width=0, shape_height=0):
        """Calcule une position absolue à partir d'une description relative"""
        rect = self.get_rectangle_bounds()
        rx, ry = rect["x"], rect["y"]
        rw, rh = rect["width"], rect["height"]

        desc_lower = position_desc.lower()

        # Centre
        if any(word in desc_lower for word in ["centre", "center", "milieu"]):
            return [(rx + rw/2, ry + rh/2)]

        positions = []

        # Coins individuels
        if any(w in desc_lower for w in ["haut gauche", "top left", "coin 1"]):
            positions.append((rx, ry + rh))
        if any(w in desc_lower for w in ["haut droit", "top right", "coin 2"]):
            positions.append((rx + rw, ry + rh))
        if any(w in desc_lower for w in ["bas droit", "bottom right", "coin 3"]):
            positions.append((rx + rw, ry))
        if any(w in desc_lower for w in ["bas gauche", "bottom left", "coin 4"]):
            positions.append((rx, ry))

        # Tous les coins
        if any(w in desc_lower for w in ["4 coins", "quatre coins", "tous les coins", "aux coins"]):
            positions = [
                (rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh),
            ]

        # Offset depuis un coin
        offset_match = re.search(r"offset\s+([\d\.+-/*$\w]+)\s+([\d\.+-/*$\w]+)", desc_lower)
        if offset_match:
            off_x = self.resolve_value(offset_match.group(1))
            off_y = self.resolve_value(offset_match.group(2))

            if any(w in desc_lower for w in ["coins", "coin"]):
                base_positions = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)]
                positions = [(p[0] + off_x, p[1] + off_y) for p in base_positions]
            else:
                positions = [(rx + off_x, ry + off_y)]

        # Coordonnées absolues
        abs_match = re.search(r"\((-?[\d\.]+)\s*,\s*(-?[\d\.]+)\)", position_desc)
        if abs_match:
            positions = [(float(abs_match.group(1)), float(abs_match.group(2)))]

        # Offset depuis le centre
        center_offset = re.search(r"centre\s+offset\s+([\d\.+-/*$\w]+)\s+([\d\.+-/*$\w]+)", desc_lower)
        if center_offset:
            off_x = self.resolve_value(center_offset.group(1))
            off_y = self.resolve_value(center_offset.group(2))
            positions = [(rx + rw/2 + off_x, ry + rh/2 + off_y)]

        if not positions:
            positions = [(rx, ry)]

        return positions

    def parse_single_operation(self, op_text):
        """Parse une seule opération"""
        op_lower = op_text.lower().strip()
        if not op_lower:
            return []

        operations = []

        # RECTANGLE
        if any(word in op_lower for word in ["rectangle", "rect", "carré", "carre", "square"]):
            nums = self.extract_numbers(op_text)
            if len(nums) >= 2:
                width = nums[0]
                height = nums[1]

                # Chercher les variables dans le texte
                dim_match = re.search(r"(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)", op_text)
                if dim_match:
                    width = float(dim_match.group(1))
                    height = float(dim_match.group(2))

                # Résoudre si ce sont des expressions
                for var_name, var_val in self.variables.items():
                    if f"${var_name}" in op_text or var_name in op_text.lower():
                        temp_text = op_text
                        for vn, vv in self.variables.items():
                            temp_text = temp_text.replace(f"${vn}", str(vv))
                        nums2 = self.extract_numbers(temp_text)
                        if len(nums2) >= 2:
                            width, height = nums2[0], nums2[1]

                x, y = 0, 0
                pos_match = re.search(r"à\s*\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)", op_text)
                if pos_match:
                    x, y = float(pos_match.group(1)), float(pos_match.group(2))

                operations.append({
                    "type": "rectangle", "x": x, "y": y,
                    "width": width, "height": height
                })
                self.last_rect = {"x": x, "y": y, "width": width, "height": height}

        # CERCLE
        elif any(word in op_lower for word in ["cercle", "circle", "rond", "round"]):
            nums = self.extract_numbers(op_text)
            radius = None

            diam_match = re.search(r"diam(?:ètre|etre)?\s*[=:]?\s*([\d\.+-/*$\w]+)", op_lower)
            if diam_match:
                radius = self.resolve_value(diam_match.group(1)) / 2

            ray_match = re.search(r"rayon\s*[=:]?\s*([\d\.+-/*$\w]+)", op_lower)
            if ray_match:
                radius = self.resolve_value(ray_match.group(1))

            if radius is None and nums:
                radius = nums[0]
                if "diam" in op_lower or "ø" in op_text:
                    radius = radius / 2

            if radius is not None:
                positions = self.calculate_position(op_text)
                for pos in positions:
                    operations.append({
                        "type": "circle", "x": pos[0], "y": pos[1], "radius": radius
                    })

        # LIGNE
        elif any(word in op_lower for word in ["ligne", "line", "trait"]):
            coords = re.findall(r"\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)", op_text)
            if len(coords) >= 2:
                x1, y1 = float(coords[0][0]), float(coords[0][1])
                x2, y2 = float(coords[1][0]), float(coords[1][1])
                operations.append({
                    "type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })

        # ARC
        elif any(word in op_lower for word in ["arc"]):
            nums = self.extract_numbers(op_text)
            if len(nums) >= 3:
                positions = self.calculate_position(op_text)
                pos = positions[0] if positions else (0, 0)
                operations.append({
                    "type": "arc", "x": pos[0], "y": pos[1],
                    "radius": nums[0], "start_angle": nums[1], "end_angle": nums[2]
                })

        # POLYGONE
        elif any(word in op_lower for word in ["polygone", "polygon", "hexagone", "pentagone"]):
            nums = self.extract_numbers(op_text)
            sides = 6
            if "hex" in op_lower: sides = 6
            elif "pent" in op_lower: sides = 5
            elif "tri" in op_lower: sides = 3
            elif "oct" in op_lower: sides = 8
            elif len(nums) >= 2: sides = int(nums[0])

            radius = nums[1] if len(nums) >= 2 else (nums[0] if nums else 50)
            positions = self.calculate_position(op_text)
            pos = positions[0] if positions else (0, 0)

            operations.append({
                "type": "polygon", "x": pos[0], "y": pos[1], "sides": sides, "radius": radius
            })

        # GRILLE
        elif any(word in op_lower for word in ["grille", "grid", "quadrillage"]):
            nums = self.extract_numbers(op_text)
            if len(nums) >= 2:
                cols, rows = int(nums[0]), int(nums[1])
                spacing = nums[2] if len(nums) > 2 else 20
                operations.append({
                    "type": "grid", "cols": cols, "rows": rows, "spacing": spacing
                })

        # ÉTOILE
        elif any(word in op_lower for word in ["étoile", "etoile", "star"]):
            nums = self.extract_numbers(op_text)
            points_count = int(nums[0]) if len(nums) >= 2 else 5
            radius = nums[1] if len(nums) >= 2 else (nums[0] if nums else 50)
            positions = self.calculate_position(op_text)
            pos = positions[0] if positions else (0, 0)

            operations.append({
                "type": "star", "x": pos[0], "y": pos[1], "points": points_count, "radius": radius
            })

        # FLÈCHE
        elif any(word in op_lower for word in ["flèche", "fleche", "arrow"]):
            nums = self.extract_numbers(op_text)
            length = nums[0] if nums else 80
            positions = self.calculate_position(op_text)
            pos = positions[0] if positions else (0, 0)

            operations.append({
                "type": "arrow", "x": pos[0], "y": pos[1], "length": length
            })

        # TEXTE
        elif any(word in op_lower for word in ["texte", "text", "écriture"]):
            text_match = re.search(r"["'](.+?)["']", op_text)
            text_content = text_match.group(1) if text_match else "TEXT"
            nums = self.extract_numbers(op_text)
            height = nums[0] if nums else 10
            positions = self.calculate_position(op_text)
            pos = positions[0] if positions else (0, 0)

            operations.append({
                "type": "text", "x": pos[0], "y": pos[1], "text": text_content, "height": height
            })

        # SPIRALE
        elif any(word in op_lower for word in ["spirale", "spiral"]):
            nums = self.extract_numbers(op_text)
            turns = int(nums[0]) if nums else 3
            radius = nums[1] if len(nums) > 1 else 50
            positions = self.calculate_position(op_text)
            pos = positions[0] if positions else (0, 0)

            operations.append({
                "type": "spiral", "x": pos[0], "y": pos[1], "turns": turns, "radius": radius
            })

        return operations

    def parse_multi_operations(self, text_input):
        """Parse un texte avec multi-opérations et variables"""
        self.entities_created = []
        all_operations = []

        # Étape 1: Extraire les variables
        self.parse_variables(text_input)

        # Étape 2: Séparer les opérations
        lines = text_input.split("\n")

        operation_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r"\$?\w+\s*=", line):
                continue
            operation_lines.append(line)

        # Si une seule ligne avec plusieurs opérations
        if len(operation_lines) == 1:
            op_starts = r"(rectangle|rect|carré|cercle|circle|ligne|line|arc|polygone|polygon|grille|grid|étoile|etoile|star|flèche|fleche|arrow|texte|text|spirale|spiral)"
            mixed_line = operation_lines[0]
            mixed_line = re.sub(r",\s*(?=" + op_starts + r")", "\n", mixed_line, flags=re.IGNORECASE)
            operation_lines = [l.strip() for l in mixed_line.split("\n") if l.strip()]

        # Étape 3: Parser chaque opération
        for line in operation_lines:
            ops = self.parse_single_operation(line)
            all_operations.extend(ops)
            for op in ops:
                self.entities_created.append(f"{op['type'].upper()}: {str(op)}")

        return all_operations

    def build_dxf(self, operations):
        """Construit le DXF à partir des opérations parsées"""
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()

        entity_count = 0

        for op in operations:
            op_type = op["type"]

            if op_type == "rectangle":
                x, y = op["x"], op["y"]
                w, h = op["width"], op["height"]
                points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
                msp.add_lwpolyline(points, close=True)
                entity_count += 1

            elif op_type == "circle":
                msp.add_circle((op["x"], op["y"]), op["radius"])
                entity_count += 1

            elif op_type == "line":
                msp.add_line((op["x1"], op["y1"]), (op["x2"], op["y2"]))
                entity_count += 1

            elif op_type == "arc":
                msp.add_arc((op["x"], op["y"]), op["radius"], op["start_angle"], op["end_angle"])
                entity_count += 1

            elif op_type == "polygon":
                x, y = op["x"], op["y"]
                sides = op["sides"]
                radius = op["radius"]
                points = []
                for i in range(sides):
                    angle = 2 * math.pi * i / sides - math.pi / 2
                    points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
                points.append(points[0])
                msp.add_lwpolyline(points, close=True)
                entity_count += 1

            elif op_type == "grid":
                cols, rows = op["cols"], op["rows"]
                spacing = op["spacing"]
                for i in range(cols + 1):
                    x = i * spacing
                    msp.add_line((x, 0), (x, rows * spacing))
                for j in range(rows + 1):
                    y = j * spacing
                    msp.add_line((0, y), (cols * spacing, y))
                entity_count += (cols + 1) + (rows + 1)

            elif op_type == "star":
                x, y = op["x"], op["y"]
                points_count = op["points"]
                radius = op["radius"]
                star_points = []
                for i in range(2 * points_count):
                    angle = math.pi * i / points_count - math.pi / 2
                    r = radius if i % 2 == 0 else radius / 2.5
                    star_points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
                star_points.append(star_points[0])
                msp.add_lwpolyline(star_points, close=True)
                entity_count += 1

            elif op_type == "arrow":
                x, y = op["x"], op["y"]
                length = op["length"]
                msp.add_line((x, y), (x + length, y))
                head_size = length * 0.15
                msp.add_line((x + length, y), (x + length - head_size, y + head_size/2))
                msp.add_line((x + length, y), (x + length - head_size, y - head_size/2))
                entity_count += 3

            elif op_type == "text":
                msp.add_text(op["text"], dxfattribs={
                    "insert": (op["x"], op["y"]), "height": op["height"]
                })
                entity_count += 1

            elif op_type == "spiral":
                x, y = op["x"], op["y"]
                turns = op["turns"]
                radius = op["radius"]
                points = []
                steps = turns * 36
                for i in range(steps + 1):
                    t = i / steps * turns * 2 * math.pi
                    r = radius * i / steps
                    points.append((x + r * math.cos(t), y + r * math.sin(t)))
                msp.add_lwpolyline(points)
                entity_count += 1

        return doc, entity_count

# ============================================
# FONCTIONS IMAGE → DXF AVEC PARAMÈTRES
# ============================================

def image_to_dxf_parametric(image_file, threshold=128, simplify=True, 
                            scale=1.0, rotation=0, mirror_h=False, mirror_v=False):
    """Convertit une image en DXF avec paramètres de modification"""
    img = Image.open(image_file)
    img_gray = img.convert("L") if img.mode != "L" else img

    # Redimensionner
    if scale != 1.0:
        new_size = (int(img_gray.width * scale), int(img_gray.height * scale))
        img_gray = img_gray.resize(new_size, Image.LANCZOS)

    # Rotation
    if rotation != 0:
        img_gray = img_gray.rotate(-rotation, expand=True, fillcolor=255)

    # Miroir
    if mirror_h:
        img_gray = img_gray.transpose(Image.FLIP_LEFT_RIGHT)
    if mirror_v:
        img_gray = img_gray.transpose(Image.FLIP_TOP_BOTTOM)

    img_array = np.array(img_gray)

    mean_val = np.mean(img_array)
    if mean_val < 128:
        img_array = 255 - img_array

    _, binary = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()

    entities_count = 0
    all_contours_data = []

    for contour in contours:
        if len(contour) < 3:
            continue
        if simplify:
            epsilon = 0.005 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
        else:
            approx = contour

        if len(approx) < 3:
            continue

        points = [(float(p[0][0]), float(p[0][1])) for p in approx]
        if points[0] != points[-1]:
            points.append(points[0])

        all_contours_data.append(points)
        msp.add_lwpolyline(points, close=True)
        entities_count += 1

    # Stocker les données pour modification paramétrique
    st.session_state.image_trace_data = {
        "contours": all_contours_data,
        "original_size": (img_gray.width, img_gray.height),
        "threshold": threshold,
        "simplify": simplify
    }

    return doc, entities_count


def modify_traced_image(scale=1.0, rotation=0, offset_x=0, offset_y=0,
                        mirror_h=False, mirror_v=False):
    """Modifie les données de tracé d'image précédemment stockées"""
    if not st.session_state.image_trace_data:
        return None

    data = st.session_state.image_trace_data
    contours = data["contours"]
    orig_w, orig_h = data["original_size"]

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()

    for contour in contours:
        new_points = []
        for px, py in contour:
            nx = px * scale
            ny = py * scale

            if rotation != 0:
                cx, cy = orig_w / 2, orig_h / 2
                angle_rad = math.radians(rotation)
                rx = cx + (nx - cx) * math.cos(angle_rad) - (ny - cy) * math.sin(angle_rad)
                ry = cy + (nx - cx) * math.sin(angle_rad) + (ny - cy) * math.cos(angle_rad)
                nx, ny = rx, ry

            if mirror_h:
                nx = orig_w * scale - nx
            if mirror_v:
                ny = orig_h * scale - ny

            nx += offset_x
            ny += offset_y

            new_points.append((nx, ny))

        if len(new_points) > 2:
            msp.add_lwpolyline(new_points, close=True)

    return doc


# ============================================
# FONCTIONS DE RÉPARATION DXF
# ============================================

def repair_dxf(dxf_file):
    """Répare un fichier DXF défectueux"""
    try:
        doc = ezdxf.readfile(dxf_file)
    except Exception as e:
        try:
            doc = ezdxf.recover.readfile(dxf_file)
        except:
            return None, f"Impossible de lire: {str(e)}"

    msp = doc.modelspace()
    repairs_made = []

    # 1. Supprimer dupliqués
    entities_to_remove = []
    seen = set()
    for entity in msp:
        try:
            dxftype = entity.dxftype()
            if dxftype == "LWPOLYLINE":
                points = tuple(tuple(p) for p in entity.get_points("xy"))
                key = ("LWPOLYLINE", points, entity.closed)
            elif dxftype == "LINE":
                key = ("LINE", tuple(entity.dxf.start), tuple(entity.dxf.end))
            elif dxftype == "CIRCLE":
                key = ("CIRCLE", tuple(entity.dxf.center), entity.dxf.radius)
            elif dxftype == "ARC":
                key = ("ARC", tuple(entity.dxf.center), entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle)
            else:
                continue
            if key in seen:
                entities_to_remove.append(entity)
            else:
                seen.add(key)
        except:
            entities_to_remove.append(entity)

    for entity in entities_to_remove:
        msp.delete_entity(entity)
    if entities_to_remove:
        repairs_made.append(f"Supprimé {len(entities_to_remove)} duplicatas/invalides")

    # 2. Fermer polylines
    closed_count = 0
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            points = list(entity.get_points("xy"))
            if len(points) > 2:
                first = np.array(points[0])
                last = np.array(points[-1])
                if np.linalg.norm(first - last) < 1.0:
                    entity.closed = True
                    closed_count += 1
    if closed_count:
        repairs_made.append(f"Fermé {closed_count} polylines")

    # 3. Lignes nulles
    zero_length = 0
    for entity in msp.query("LINE"):
        if np.linalg.norm(np.array(entity.dxf.start) - np.array(entity.dxf.end)) < 0.001:
            msp.delete_entity(entity)
            zero_length += 1
    if zero_length:
        repairs_made.append(f"Supprimé {zero_length} lignes nulles")

    # 4. Cercles invalides
    bad_circles = 0
    for entity in msp.query("CIRCLE"):
        if entity.dxf.radius <= 0:
            msp.delete_entity(entity)
            bad_circles += 1
    if bad_circles:
        repairs_made.append(f"Supprimé {bad_circles} cercles invalides")

    # 5. Détecter taille anormale
    try:
        extents = bbox.extents(msp)
        if extents.extmin and extents.extmax:
            bounds_size = max(
                abs(extents.extmax[0] - extents.extmin[0]),
                abs(extents.extmax[1] - extents.extmin[1])
            )
            if bounds_size > 1e6:
                repairs_made.append("⚠️ Dessin très grand détecté")
    except:
        pass

    if not repairs_made:
        repairs_made.append("✅ Aucun problème majeur détecté")

    return doc, repairs_made


# ============================================
# FONCTIONS DE PRÉVISUALISATION
# ============================================

def dxf_to_svg_preview(doc, width=800, height=600):
    """Convertit un DXF en SVG pour prévisualisation"""
    msp = doc.modelspace()

    try:
        extents = bbox.extents(msp)
        min_x, min_y = extents.extmin[0], extents.extmin[1]
        max_x, max_y = extents.extmax[0], extents.extmax[1]
    except:
        min_x, min_y, max_x, max_y = -100, -100, 100, 100

    margin = 20
    dx = max_x - min_x or 100
    dy = max_y - min_y or 100

    scale = min((width - 2 * margin) / dx, (height - 2 * margin) / dy)
    offset_x = margin + (width - 2 * margin - dx * scale) / 2 - min_x * scale
    offset_y = height - (margin + (height - 2 * margin - dy * scale) / 2) + min_y * scale

    def transform(point):
        return (point[0] * scale + offset_x, offset_y - point[1] * scale)

    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#f8f9fa"/>',
        '<g stroke="#1f77b4" stroke-width="1.5" fill="none">'
    ]

    for entity in msp:
        try:
            dxftype = entity.dxftype()

            if dxftype == "LWPOLYLINE":
                points = entity.get_points("xy")
                if len(points) > 1:
                    path_data = "M " + " L ".join(f"{transform(p)[0]:.2f},{transform(p)[1]:.2f}" for p in points)
                    if entity.closed:
                        path_data += " Z"
                    svg_parts.append(f'<path d="{path_data}"/>')

            elif dxftype == "LINE":
                p1 = transform(entity.dxf.start)
                p2 = transform(entity.dxf.end)
                svg_parts.append(f'<line x1="{p1[0]:.2f}" y1="{p1[1]:.2f}" x2="{p2[0]:.2f}" y2="{p2[1]:.2f}"/>')

            elif dxftype == "CIRCLE":
                center = transform(entity.dxf.center)
                r = entity.dxf.radius * scale
                svg_parts.append(f'<circle cx="{center[0]:.2f}" cy="{center[1]:.2f}" r="{r:.2f}"/>')

            elif dxftype == "ARC":
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                x1 = center[0] + radius * math.cos(start_angle)
                y1 = center[1] + radius * math.sin(start_angle)
                x2 = center[0] + radius * math.cos(end_angle)
                y2 = center[1] + radius * math.sin(end_angle)
                p1 = transform((x1, y1))
                p2 = transform((x2, y2))
                c = transform(center)
                r = radius * scale
                large_arc = 1 if abs(end_angle - start_angle) > math.pi else 0
                svg_parts.append(f'<path d="M {p1[0]:.2f},{p1[1]:.2f} A {r:.2f},{r:.2f} 0 {large_arc} 1 {p2[0]:.2f},{p2[1]:.2f}"/>')

            elif dxftype == "TEXT":
                insert = transform(entity.dxf.insert)
                text = entity.dxf.text
                height = max(entity.dxf.height * scale, 12)
                svg_parts.append(f'<text x="{insert[0]:.2f}" y="{insert[1]:.2f}" font-size="{height:.1f}" fill="#1f77b4" stroke="none" text-anchor="middle">{text}</text>')
        except:
            continue

    svg_parts.append('</g></svg>')
    return "\n".join(svg_parts)

# ============================================
# INTERFACE STREAMLIT
# ============================================

st.set_page_config(
    page_title=f"{APP_NAME} — AI 2D Design",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .section-header { font-size: 1.4rem; font-weight: bold; color: #ff7f0e; margin-top: 1rem; margin-bottom: 1rem; }
    .info-box { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .success-box { background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .warning-box { background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; border: 2px solid #ffc107; }
    .error-box { background-color: #f8d7da; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; border: 2px solid #dc3545; }
    .license-banner { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .code-example { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; margin: 10px 0; }
    .stButton>button { width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

init_session_state()

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="font-size: 3rem;">{APP_ICON}</div>
        <div style="font-size: 1.3rem; font-weight: bold; color: #1f77b4;">{APP_NAME}</div>
        <div style="font-size: 0.8rem; color: #666;">AI 2D Design</div>
    </div>
    """, unsafe_allow_html=True)

    show_user_profile()
    st.markdown("---")

    st.header("📖 Guide Paramétrique")
    st.markdown("""
    ### Variables
    Définissez des variables en début de texte:
    ```
    largeur = 120
    longueur = 45
    ```

    ### Positions Relatives
    - `au centre` → centre du dernier rectangle
    - `aux 4 coins` → les 4 coins du rectangle
    - `offset X Y` → décalage depuis les coins
    - `coin haut gauche` → coin spécifique

    ### Multi-opérations
    Séparez par des sauts de ligne:
    ```
    rectangle 120x45
    cercle diametre 10 au centre
    cercle diametre 6 aux 4 coins offset 10 10
    ```
    """)

    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; font-size: 0.75rem; color: #999;">
        © 2026 {APP_NAME}<br>
        {CONTACT_EMAIL}
    </div>
    """, unsafe_allow_html=True)

# Modals
if st.session_state.show_login_modal:
    st.markdown("---")
    simulate_gmail_login()
    st.markdown("---")
    st.stop()

if st.session_state.show_license_modal:
    st.markdown("---")
    show_license_activation()
    st.markdown("---")
    st.stop()

# Header
st.markdown(f'<div class="main-header">{APP_ICON} {APP_NAME}</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Design Paramétrique 2D Intelligent en DXF</div>', unsafe_allow_html=True)

# Bannière licence
if not st.session_state.license_activated:
    remaining = get_remaining_requests()
    if remaining > 0:
        st.markdown(f"""
        <div class="license-banner">
            🎁 <b>Mode Gratuit</b> — {remaining} requête(s) restante(s) sur {FREE_REQUESTS_LIMIT}<br>
            <small>Passez à la version complète pour un accès illimité</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="error-box" style="text-align: center;">
            ⛔ <b>Limite gratuite atteinte</b><br>
            Contactez <b>{CONTACT_EMAIL}</b> pour obtenir une clé de licence
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔑 Activer une licence", type="primary", use_container_width=True):
                st.session_state.show_license_modal = True
                st.rerun()
        st.stop()

if not st.session_state.is_logged_in:
    st.markdown("""
    <div class="warning-box" style="text-align: center;">
        <h3>🔒 Connexion requise</h3>
        <p>Veuillez vous connecter avec votre compte Gmail.</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Se connecter avec Gmail", type="primary", use_container_width=True):
            st.session_state.show_login_modal = True
            st.rerun()
    st.stop()

# ============================================
# ONGLETS
# ============================================

tab1, tab2, tab3 = st.tabs(["📝 Texte → DXF", "🖼️ Image → DXF", "🔧 Réparer DXF"])

# === ONGLET 1: TEXTE → DXF PARAMÉTRIQUE ===
with tab1:
    st.markdown('<div class="section-header">📝 Design Paramétrique Texte → DXF</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("""
        **Syntaxe paramétrique avancée:**

        **Variables:**
        ```
        largeur = 120
        longueur = 45
        diam_centre = 10
        diam_coin = 6
        offset_coin = 10
        ```

        **Opérations avec positions relatives:**
        ```
        rectangle largeur x longueur
        cercle diametre diam_centre au centre
        cercle diametre diam_coin aux 4 coins offset offset_coin offset_coin
        ```

        **Positions supportées:**
        - `au centre` / `centre` / `milieu`
        - `aux 4 coins` / `quatre coins`
        - `coin haut gauche` / `top left`
        - `offset X Y` (décalage depuis les coins)
        - Coordonnées absolues: `(50, 30)`
        """)
        st.markdown('</div>', unsafe_allow_html=True)

        # Exemple pré-rempli
        default_text = """largeur = 120
longueur = 45
rectangle largeur x longueur
cercle diametre 10 au centre
cercle diametre 6 aux 4 coins offset 10 10"""

        text_input = st.text_area(
            "Votre design paramétrique:",
            value=default_text,
            height=200,
            placeholder="Définissez vos variables et opérations ici..."
        )

        if st.button("🚀 Générer DXF", type="primary", use_container_width=True):
            if not can_make_request():
                st.session_state.show_license_modal = True
                st.rerun()

            with st.spinner("Analyse paramétrique et génération..."):
                try:
                    parser = ParametricParser()
                    operations = parser.parse_multi_operations(text_input)

                    if not operations:
                        st.warning("⚠️ Aucune opération reconnue. Vérifiez votre syntaxe.")
                    else:
                        doc, entity_count = parser.build_dxf(operations)
                        increment_request()

                        st.session_state.generated_doc = doc
                        st.session_state.generated_svg = dxf_to_svg_preview(doc)
                        st.session_state.parametric_vars = parser.variables

                        st.success(f"✅ {entity_count} entité(s) créée(s) à partir de {len(operations)} opération(s)")

                        # Afficher les variables résolues
                        if parser.variables:
                            st.markdown("**Variables utilisées:**")
                            for var, val in parser.variables.items():
                                st.write(f"  • ${var} = {val}")

                        # Afficher les opérations détectées
                        st.markdown("**Opérations:**")
                        for i, op in enumerate(operations, 1):
                            st.write(f"  {i}. {op['type'].upper()}: {op}")

                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

    with col2:
        st.markdown('<div class="section-header">👁️ Prévisualisation</div>', unsafe_allow_html=True)

        if st.session_state.generated_svg:
            st.components.v1.html(st.session_state.generated_svg, height=450)

            if st.session_state.generated_doc:
                with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                    st.session_state.generated_doc.saveas(tmp.name)
                    tmp_path = tmp.name

                with open(tmp_path, "rb") as f_dxf:
                    dxf_bytes = f_dxf.read()
                os.unlink(tmp_path)

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label="⬇️ Télécharger DXF",
                        data=dxf_bytes,
                        file_name="myindustryai_parametric.dxf",
                        mime="application/dxf",
                        use_container_width=True
                    )
                with col_dl2:
                    svg_data = st.session_state.generated_svg.encode("utf-8")
                    st.download_button(
                        label="⬇️ Télécharger SVG",
                        data=svg_data,
                        file_name="myindustryai_preview.svg",
                        mime="image/svg+xml",
                        use_container_width=True
                    )
        else:
            st.info("La prévisualisation apparaîtra ici après génération")

            st.markdown("""
            <div style="background: #e9ecef; padding: 20px; border-radius: 10px; text-align: center;">
                <p style="color: #666;">👈 Entrez votre design paramétrique à gauche</p>
                <p style="font-size: 0.8rem; color: #999;">Exemple: rectangle avec trous aux coins</p>
            </div>
            """, unsafe_allow_html=True)

# === ONGLET 2: IMAGE → DXF AVEC PARAMÈTRES ===
with tab2:
    st.markdown('<div class="section-header">🖼️ Image → DXF avec Paramètres</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_image = st.file_uploader(
            "Choisir une image",
            type=['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'],
            help="Uploadez une image à vectoriser et modifier"
        )

        if uploaded_image:
            img = Image.open(uploaded_image)
            st.image(img, caption="Image originale", use_column_width=True)

            st.markdown("---")
            st.subheader("⚙️ Paramètres de vectorisation")

            threshold = st.slider("Seuil de binarisation", 0, 255, 128)
            simplify = st.checkbox("Simplifier les contours", value=True)

            st.markdown("---")
            st.subheader("📐 Paramètres de modification")

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                scale = st.number_input("Échelle", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
                rotation = st.number_input("Rotation (°)", min_value=-360.0, max_value=360.0, value=0.0, step=15.0)
            with col_s2:
                offset_x = st.number_input("Offset X", value=0.0, step=10.0)
                offset_y = st.number_input("Offset Y", value=0.0, step=10.0)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mirror_h = st.checkbox("Miroir Horizontal", value=False)
            with col_m2:
                mirror_v = st.checkbox("Miroir Vertical", value=False)

            if st.button("🔄 Convertir en DXF", type="primary", use_container_width=True):
                if not can_make_request():
                    st.session_state.show_license_modal = True
                    st.rerun()

                with st.spinner("Vectorisation et modification..."):
                    try:
                        uploaded_image.seek(0)
                        doc, count = image_to_dxf_parametric(
                            uploaded_image, threshold, simplify,
                            scale, rotation, mirror_h, mirror_v
                        )
                        increment_request()

                        # Appliquer offset si nécessaire
                        if offset_x != 0 or offset_y != 0:
                            doc = modify_traced_image(scale, rotation, offset_x, offset_y, mirror_h, mirror_v)

                        svg_preview = dxf_to_svg_preview(doc)

                        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                            doc.saveas(tmp.name)
                            tmp_path = tmp.name

                        with open(tmp_path, "rb") as f_dxf:
                            dxf_bytes = f_dxf.read()
                        os.unlink(tmp_path)

                        st.session_state.image_dxf_bytes = dxf_bytes
                        st.session_state.image_dxf_svg = svg_preview

                        st.success(f"✅ {count} forme(s) vectorisée(s) et modifiée(s)")
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")

    with col2:
        st.markdown('<div class="section-header">👁️ Résultat DXF</div>', unsafe_allow_html=True)

        if 'image_dxf_svg' in st.session_state and st.session_state.image_dxf_svg:
            st.components.v1.html(st.session_state.image_dxf_svg, height=400)

            if 'image_dxf_bytes' in st.session_state:
                st.download_button(
                    label="⬇️ Télécharger DXF",
                    data=st.session_state.image_dxf_bytes,
                    file_name="myindustryai_image.dxf",
                    mime="application/dxf",
                    use_container_width=True
                )
        else:
            st.info("Le résultat apparaîtra ici")

# === ONGLET 3: RÉPARER DXF ===
with tab3:
    st.markdown('<div class="section-header">🔧 Réparation Automatique de DXF</div>', unsafe_allow_html=True)

    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    **Réparations automatiques:**
    - ✅ Supprime les entités dupliquées
    - ✅ Ferme les polylines presque fermées
    - ✅ Supprime les lignes de longueur nulle
    - ✅ Élimine les cercles avec rayon invalide
    - ✅ Supprime les entités corrompues
    - ✅ Récupère les fichiers endommagés (recover)
    - ✅ Détecte les dessins de taille anormale
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_dxf = st.file_uploader(
            "Choisir un fichier DXF",
            type=['dxf'],
            help="Uploadez un DXF défectueux"
        )

        if uploaded_dxf:
            st.info(f"Fichier: **{uploaded_dxf.name}** | {len(uploaded_dxf.getvalue())} octets")

            if st.button("🔧 Réparer le DXF", type="primary", use_container_width=True):
                if not can_make_request():
                    st.session_state.show_license_modal = True
                    st.rerun()

                with st.spinner("Analyse et réparation..."):
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                            tmp.write(uploaded_dxf.getvalue())
                            tmp_path = tmp.name

                        doc, repairs = repair_dxf(tmp_path)
                        os.unlink(tmp_path)

                        if doc is None:
                            st.error(f"❌ {repairs}")
                        else:
                            increment_request()

                            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                                doc.saveas(tmp.name)
                                repaired_path = tmp.name

                            with open(repaired_path, "rb") as f_dxf:
                                repaired_bytes = f_dxf.read()
                            os.unlink(repaired_path)

                            st.session_state.repaired_dxf_bytes = repaired_bytes
                            st.session_state.repaired_dxf_repairs = repairs
                            st.session_state.repaired_dxf_svg = dxf_to_svg_preview(doc)

                            st.success("✅ Réparation terminée!")
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")

    with col2:
        if 'repaired_dxf_repairs' in st.session_state:
            st.markdown('<div class="section-header">📋 Rapport de réparation</div>', unsafe_allow_html=True)

            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            for repair in st.session_state.repaired_dxf_repairs:
                st.write(f"✓ {repair}")
            st.markdown('</div>', unsafe_allow_html=True)

            if 'repaired_dxf_svg' in st.session_state and st.session_state.repaired_dxf_svg:
                st.components.v1.html(st.session_state.repaired_dxf_svg, height=350)

            if 'repaired_dxf_bytes' in st.session_state:
                st.download_button(
                    label="⬇️ Télécharger DXF réparé",
                    data=st.session_state.repaired_dxf_bytes,
                    file_name="myindustryai_repaired.dxf",
                    mime="application/dxf",
                    use_container_width=True
                )
        else:
            st.info("Le rapport apparaîtra ici")

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #666; font-size: 0.85rem;'>"
    f"{APP_ICON} {APP_NAME} | © 2026 | Contact: {CONTACT_EMAIL}"
    f"</div>",
    unsafe_allow_html=True
)
