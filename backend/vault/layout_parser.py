import math
from typing import List, Dict, Any

class LayoutParser:
    @staticmethod
    def build_spatial_graph(words: List[Dict[str, Any]], row_tolerance: float = 12.0) -> Dict[str, Any]:
        """
        Builds a spatial graph from OCR words.
        Groups words into rows based on y-center proximity.
        Links neighbors left/right/above/below.
        """
        if not words:
            return {"words": [], "rows": [], "text_by_row": []}

        # Sort words primarily by Y-coordinate, then by X-coordinate
        sorted_words = sorted(words, key=lambda w: (w["center"][1], w["center"][0]))
        
        rows = []
        current_row = []
        current_row_y = sorted_words[0]["center"][1]

        for w in sorted_words:
            if abs(w["center"][1] - current_row_y) <= row_tolerance:
                current_row.append(w)
                # Update running average of row Y
                current_row_y = sum(cw["center"][1] for cw in current_row) / len(current_row)
            else:
                # Sort current row strictly by X
                current_row.sort(key=lambda cw: cw["center"][0])
                rows.append(current_row)
                current_row = [w]
                current_row_y = w["center"][1]

        if current_row:
            current_row.sort(key=lambda cw: cw["center"][0])
            rows.append(current_row)

        # Annotate words with row/col and neighbors
        word_nodes = []
        text_by_row = []
        
        for r_idx, row in enumerate(rows):
            row_text = " ".join([w["text"] for w in row])
            text_by_row.append(row_text)
            
            for c_idx, w in enumerate(row):
                w["row_idx"] = r_idx
                w["col_idx"] = c_idx
                w["neighbors"] = {
                    "left": row[c_idx - 1] if c_idx > 0 else None,
                    "right": row[c_idx + 1] if c_idx < len(row) - 1 else None,
                    "above": None,
                    "below": None
                }
                
                # Find vertical neighbors (closest center-X in adjacent rows)
                if r_idx > 0:
                    above_row = rows[r_idx - 1]
                    closest_above = min(above_row, key=lambda cw: abs(cw["center"][0] - w["center"][0]))
                    if abs(closest_above["center"][0] - w["center"][0]) < 150: # Threshold for vertical alignment
                        w["neighbors"]["above"] = closest_above
                        
                if r_idx < len(rows) - 1:
                    below_row = rows[r_idx + 1]
                    closest_below = min(below_row, key=lambda cw: abs(cw["center"][0] - w["center"][0]))
                    if abs(closest_below["center"][0] - w["center"][0]) < 150:
                        w["neighbors"]["below"] = closest_below

                word_nodes.append(w)

        return {
            "words": word_nodes,
            "rows": rows,
            "text_by_row": text_by_row,
            "full_text": "\n".join(text_by_row)
        }

    @staticmethod
    def find_keyword_anchor(graph: Dict[str, Any], keywords: List[str], search_direction: str = "right") -> Dict[str, Any]:
        """
        Finds a keyword and returns the adjacent word/text block in the specified direction.
        Directions: 'right', 'below', 'row_rest'
        """
        for r_idx, row in enumerate(graph.get("rows", [])):
            for c_idx, w in enumerate(row):
                text_lower = w["text"].lower()
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        # Found anchor
                        if search_direction == "right" and w["neighbors"]["right"]:
                            return {"value": w["neighbors"]["right"]["text"], "conf": w["neighbors"]["right"]["confidence"], "anchor": w["text"]}
                        elif search_direction == "below" and w["neighbors"]["below"]:
                            # Often fields span multiple words below
                            below_word = w["neighbors"]["below"]
                            below_row = graph["rows"][below_word["row_idx"]]
                            # Gather the rest of the below row starting from that col
                            val = " ".join([cw["text"] for cw in below_row[below_word["col_idx"]:]])
                            return {"value": val, "conf": below_word["confidence"], "anchor": w["text"]}
                        elif search_direction == "row_rest":
                            # Everything to the right in the same row
                            val = " ".join([cw["text"] for cw in row[c_idx+1:]])
                            if val:
                                return {"value": val, "conf": 95.0, "anchor": w["text"]}
        return None
