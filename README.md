# Blender Reify

**Blender Reify** is a collection of tools designed to enhance Blender's capabilities for modeling 3D printable items.

## Features

- **Batch STL Export:** Effortlessly export multiple mesh objects to STL format.
- **Auto-Fix Non-Manifold Geometry:** Detects and fixes non-manifold geometry, holes, flipped normals, and duplicate vertices.
- **Gothic Architecture Tools:** Generate Gothic elements such as pointed arches, rib vaults, flying buttresses, tracery, gargoyles, spires, and lancet windows.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/ramsesoriginal/blender_reify.git
   ```

2. **Add to Blender:**

   - Open Blender.
   - Navigate to `Edit` > `Preferences` > `Add-ons` > `Install`.
   - Select the `blender_reify` folder or specific scripts to install.

## Usage

1. **Enable the Add-on:**

   - Go to `Edit` > `Preferences` > `Add-ons`.
   - Search for "Blender Reify" and enable it.

2. **Access Tools:**
   - The tools can be found in the `3D Viewport` under the `Tool Shelf` or `N-panel`.

3. **Batch STL Export:**
   - Use the "Batch Export STL" operator to export visible mesh objects.

4. **Auto-Fix Non-Manifold Geometry:**
   - Navigate to the `3D Viewport` > `Tool Shelf` > `Tools Tab`.
   - Click on **Fix Non-Manifold Geometry** to automatically clean all visible mesh objects.

4. **Gothic Architecture Tools:**
   - Navigate to the `3D Viewport` > `Tool Shelf` > `Gothic Tools`.
   - Provides various operators for generating and modifying Gothic structures:
      - Pointed Arches
      - Pointed Rib Vaults
      - Flying Buttresses
      - Divine Flying Buttresses (Inspired by grand Gothic cathedrals)
      - Tracery
      - Gargoyles
      - Spires
      - Lancet Windows
         - Converts inset geometry into pointed Gothic-style windows with smooth curvature.
         - Adjustable settings for segment count, curvature, and proportions.

## Contributing

Contributions are welcome! Please check [the issues](https://github.com/ramsesoriginal/blender_reify/issues) for ideas or submit your own.

1. **Fork the Repository.**

2. **Create a New Branch:**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

3. **Commit Your Changes:**

   ```bash
   git commit -m 'Add Your Feature'
   ```

4. **Push to the Branch:**

   ```bash
   git push origin feature/YourFeatureName
   ```

5. **Open a Pull Request.**

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the Blender community and various open-source projects.
