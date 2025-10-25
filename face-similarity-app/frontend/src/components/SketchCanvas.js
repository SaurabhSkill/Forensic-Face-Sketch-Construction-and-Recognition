import React from 'react';
import html2canvas from 'html2canvas';
import ComponentLibrary from './ComponentLibrary';
import Canvas from './Canvas';
import ControlsPanel from './ControlsPanel';
import LayersPanel from './LayersPanel';

function SketchCanvas() {
  const [placedComponents, setPlacedComponents] = React.useState([]);
  const [selectedComponentId, setSelectedComponentId] = React.useState(null);
  const [exportedImage, setExportedImage] = React.useState(null);
  const canvasRef = React.useRef(null);
  const [templateEnabled, setTemplateEnabled] = React.useState(true);
  const [templateOpacity, setTemplateOpacity] = React.useState(0.25);

  const handleSelectComponent = (imagePath) => {
    const newComponent = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      imagePath,
      x: 50,
      y: 50,
      width: 100,
      rotation: 0,
      hidden: false,
      locked: false
    };
    setPlacedComponents((prev) => [...prev, newComponent]);
  };

  const updateComponentPosition = (id, x, y) => {
    setPlacedComponents((prev) => prev.map((c) => {
      if (c.id === id) {
        return { ...c, x, y };
      }
      return c;
    }));
  };

  const handleSelectForEditing = (id) => {
    setSelectedComponentId(id);
  };

  const updateComponentProps = (id, updates) => {
    setPlacedComponents((prev) => prev.map((c) => (c.id === id ? { ...c, ...updates } : c)));
  };

  const toggleVisibility = (id) => updateComponentProps(id, { hidden: !placedComponents.find((c) => c.id === id)?.hidden });
  const toggleLock = (id) => updateComponentProps(id, { locked: !placedComponents.find((c) => c.id === id)?.locked });
  const deleteComponent = (id) => setPlacedComponents((prev) => prev.filter((c) => c.id !== id));
  const duplicateComponent = (id) => {
    const target = placedComponents.find((c) => c.id === id);
    if (!target) return;
    const clone = { ...target, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, x: target.x + 10, y: target.y + 10 };
    setPlacedComponents((prev) => [clone, ...prev]);
  };
  const reorderComponents = (fromIndex, toIndex) => {
    setPlacedComponents((prev) => {
      const arr = [...prev];
      const [moved] = arr.splice(fromIndex, 1);
      arr.splice(toIndex, 0, moved);
      return arr;
    });
  };
  const containerStyle = {
    display: 'grid',
    gridTemplateColumns: '280px 1fr 320px',
    gap: '24px',
    alignItems: 'stretch',
    width: '100%',
    height: 'calc(100vh - 120px)',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    padding: '24px',
    background: '#fafafa',
    color: '#111827'
  };

  const sidebarStyle = {
    width: '280px',
    borderRight: '1px solid #e5e7eb',
    paddingRight: '16px',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden'
  };

  const mainStyle = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden'
  };

  const headerStyle = {
    marginBottom: '16px',
    fontSize: '20px',
    fontWeight: 600,
    color: '#111827'
  };

  const handleExport = async () => {
    if (!canvasRef.current) return;
    const canvas = await html2canvas(canvasRef.current, { backgroundColor: null });
    const dataUrl = canvas.toDataURL('image/png');
    setExportedImage(dataUrl);
  };

  const handleDownload = async (format) => {
    if (!canvasRef.current) return;
    const isPng = format === 'png';
    const canvas = await html2canvas(canvasRef.current, { backgroundColor: isPng ? null : '#ffffff' });
    const mime = isPng ? 'image/png' : 'image/jpeg';
    const quality = isPng ? undefined : 0.92;
    const dataUrl = canvas.toDataURL(mime, quality);
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = `sketch.${isPng ? 'png' : 'jpg'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ 
      color: '#111827', 
      padding: '24px',
      height: '100vh',
      background: '#f8fafc',
      overflow: 'hidden'
    }}>
      <h2 style={{ 
        marginBottom: '24px', 
        fontSize: '28px',
        fontWeight: 700,
        color: '#111827'
      }}>Sketch Tool (Phase 2)</h2>
      <div style={containerStyle}>
        <aside style={sidebarStyle}>
          <div style={headerStyle}>Component Library</div>
          <ComponentLibrary onSelectComponent={handleSelectComponent} />
        </aside>
        <main style={mainStyle}>
          <div style={headerStyle}>Canvas</div>
          <Canvas
            placedComponents={placedComponents}
            updateComponentPosition={updateComponentPosition}
            selectedComponentId={selectedComponentId}
            handleSelectForEditing={handleSelectForEditing}
            updateComponentProps={updateComponentProps}
            canvasRef={canvasRef}
            templateEnabled={templateEnabled}
            templateOpacity={templateOpacity}
          />
          <div style={{ marginTop: '12px', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button onClick={handleExport} style={{
              padding: '8px 12px',
              background: '#111827',
              color: '#ffffff',
              border: '1px solid #111827',
              borderRadius: '6px',
              cursor: 'pointer'
            }}>Preview Export</button>
            <button onClick={() => handleDownload('jpg')} style={{
              padding: '8px 12px',
              background: '#16a34a',
              color: '#ffffff',
              border: '1px solid #16a34a',
              borderRadius: '6px',
              cursor: 'pointer'
            }}>Save Sketch (JPEG)</button>
            <button onClick={() => handleDownload('png')} style={{
              padding: '8px 12px',
              background: '#2563eb',
              color: '#ffffff',
              border: '1px solid #2563eb',
              borderRadius: '6px',
              cursor: 'pointer'
            }}>Save Sketch (PNG)</button>
          </div>

          {exportedImage && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ marginBottom: '8px', fontWeight: 600 }}>Export Preview</div>
              <img src={exportedImage} alt="Exported Sketch" style={{ maxWidth: '100%', border: '1px solid #e5e7eb', borderRadius: '6px' }} />
            </div>
          )}
        </main>
        <div style={{
          width: '320px',
          borderLeft: '1px solid #e5e7eb',
          paddingLeft: '16px',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden'
        }}>
          <ControlsPanel
            selectedComponent={placedComponents.find((c) => c.id === selectedComponentId) || null}
            updateComponentProps={updateComponentProps}
            templateEnabled={templateEnabled}
            setTemplateEnabled={setTemplateEnabled}
            templateOpacity={templateOpacity}
            setTemplateOpacity={setTemplateOpacity}
          />
          <LayersPanel
            components={placedComponents}
            selectedId={selectedComponentId}
            onSelect={handleSelectForEditing}
            onToggleVisibility={toggleVisibility}
            onToggleLock={toggleLock}
            onDelete={deleteComponent}
            onDuplicate={duplicateComponent}
            onReorder={reorderComponents}
          />
        </div>
      </div>
    </div>
  );
}

export default SketchCanvas;


