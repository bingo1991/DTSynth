"""Device Tree Blob (DTB) Parser Module

This module provides a core class for parsing Device Tree Blob files using pylibfdt.
It enables traversal of the device tree structure, extraction of properties,
and resolution of phandle references within the tree.
"""

from typing import Any, Dict, List, Optional, Union
import fdt


class FdtNode:
    """Wrapper class for FDT nodes to provide consistent interface."""
    
    def __init__(self, name: str, path: str, properties: Dict[str, Any], children: List['FdtNode']):
        self.name = name
        self.path = path
        self.properties = properties
        self.children = children


class DtbParser:
    """Core class for parsing Device Tree Blob files using pylibfdt."""
    
    def __init__(self, dtb_path: Union[str, bytes]):
        """Initialize the parser with a DTB file path or bytes data.
        
        Args:
            dtb_path: Path to the DTB file or bytes containing DTB data
        """
        if isinstance(dtb_path, str):
            with open(dtb_path, 'rb') as f:
                dtb_data = f.read()
        else:
            dtb_data = dtb_path
            
        self._dtb = fdt.parse_dtb(dtb_data)
        self._phandle_map = self._build_phandle_map()

    def _build_phandle_map(self) -> Dict[int, str]:
        """Build a mapping from phandle values to node paths."""
        phandle_map: Dict[int, str] = {}
        
        def traverse_for_phandle(node_path: str, node: fdt.Node) -> None:
            # Check if the node has a phandle property
            try:
                phandle_prop = node.get_property('phandle')
                if phandle_prop:
                    phandle_val = int.from_bytes(phandle_prop.data[:4], byteorder='big')
                    phandle_map[phandle_val] = node_path
            except KeyError:
                pass
                
            # Recursively check children
            for child_name, child_node in node.subnodes():
                child_path = f"{node_path}/{child_name}" if node_path != '/' else f"/{child_name}"
                traverse_for_phandle(child_path, child_node)
        
        root = self._dtb
        traverse_for_phandle('/', root)
        return phandle_map

    def get_root_node(self) -> FdtNode:
        """Return the root node of the device tree."""
        return self._convert_fdt_node_to_custom('/', self._dtb)

    def _convert_fdt_node_to_custom(self, path: str, fdt_node: fdt.Node) -> FdtNode:
        """Convert an fdt.Node to our custom FdtNode object."""
        # Extract properties
        props: Dict[str, Any] = {}
        for prop_name, prop_value in fdt_node.props():
            props[prop_name] = self._decode_property(prop_value)
        
        # Process children
        children: List[FdtNode] = []
        for child_name, child_node in fdt_node.subnodes():
            child_path = f"{path}/{child_name}" if path != '/' else f"/{child_name}"
            children.append(self._convert_fdt_node_to_custom(child_path, child_node))
        
        node_name = path.split('/')[-1] if path != '/' else ''
        return FdtNode(name=node_name, path=path, properties=props, children=children)

    def _decode_property(self, prop_value: fdt.Property) -> Any:
        """Decode property value based on its content."""
        data = prop_value.data
        
        # Handle string properties (null-terminated)
        if b'\x00' in data and not all(b == 0 for b in data):
            # Multiple strings separated by nulls
            string_parts = data.split(b'\x00')
            # Filter out empty parts at the end
            string_parts = [part.decode('utf-8', errors='ignore') for part in string_parts if part]
            return string_parts[0] if len(string_parts) == 1 else string_parts
        
        # Handle cell properties (addresses/sizes)
        elif len(data) % 4 == 0 and len(data) > 0:
            cells = []
            for i in range(0, len(data), 4):
                cell_data = data[i:i+4]
                cell_value = int.from_bytes(cell_data, byteorder='big')
                cells.append(cell_value)
            
            # If it's a single cell, return as int; otherwise as list
            if len(cells) == 1:
                return cells[0]
            else:
                return cells
        
        # Handle raw binary data
        else:
            return data

    def traverse_tree(self) -> List[Dict[str, Any]]:
        """Traverse the entire device tree and return a structured representation.
        
        Returns:
            A list of dictionaries representing the tree structure with properties and children
        """
        def build_node_dict(path: str, fdt_node: fdt.Node) -> Dict[str, Any]:
            # Extract properties
            props: Dict[str, Any] = {}
            for prop_name, prop_value in fdt_node.props():
                props[prop_name] = self._decode_property(prop_value)
            
            # Get the node name from the path
            node_name = path.split('/')[-1] if path != '/' else ''
            
            # Determine address if available (usually encoded in the node name)
            address = None
            if '@' in node_name:
                address = node_name.split('@')[1]
            
            # Process children recursively
            children: List[Dict[str, Any]] = []
            for child_name, child_node in fdt_node.subnodes():
                child_path = f"{path}/{child_name}" if path != '/' else f"/{child_name}"
                children.append(build_node_dict(child_path, child_node))
            
            return {
                "path": path,
                "name": node_name,
                "address": address,
                "props": props,
                "children": children
            }
        
        root = self._dtb
        return [build_node_dict('/', root)]

    def get_compatible_strings(self) -> List[str]:
        """Extract compatible strings from the root node.
        
        Returns:
            List of compatible strings from the root node's 'compatible' property
        """
        try:
            compatible_prop = self._dtb.get_property('compatible')
            if compatible_prop:
                # Decode the property value
                data = compatible_prop.data
                # Compatible strings are null-separated
                string_parts = data.split(b'\x00')
                # Filter out empty parts and decode
                return [part.decode('utf-8', errors='ignore') for part in string_parts if part]
        except KeyError:
            pass
        
        return []

    def resolve_phandle(self, phandle_value: int) -> Optional[str]:
        """Resolve a phandle value to its corresponding node path.
        
        Args:
            phandle_value: The phandle integer value to resolve
            
        Returns:
            The path of the node with the given phandle, or None if not found
        """
        return self._phandle_map.get(phandle_value)