"""Shared tree widget for folder-structure previews."""

from typing import Dict, List

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem


class FolderPreviewWidget(QTreeWidget):
    """Tree widget showing a preview of the proposed folder structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Proposed Structure"])
        self.setRootIsDecorated(True)

    def update_preview(self, preview: Dict[str, List[str]]) -> None:
        """Populate the tree from a folder-path -> file-list mapping."""
        self.clear()
        if not preview:
            return

        folder_items: Dict[str, QTreeWidgetItem] = {}

        for folder_path, files in sorted(preview.items()):
            parts = folder_path.strip("/").split("/") if folder_path else []

            current_parent = None
            current_path = ""

            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                if current_path not in folder_items:
                    node = QTreeWidgetItem([f"📁 {part}"])
                    if current_parent is not None:
                        current_parent.addChild(node)
                    else:
                        self.addTopLevelItem(node)
                    folder_items[current_path] = node
                current_parent = folder_items[current_path]

            parent_item = current_parent if current_parent is not None else self.invisibleRootItem()
            for filename in sorted(files):
                parent_item.addChild(QTreeWidgetItem([f"📄 {filename}"]))

        self.expandAll()
