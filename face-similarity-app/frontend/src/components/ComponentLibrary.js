import React from 'react';

function ComponentLibrary({ onSelectComponent }) {
  const placeholderSvg = `data:image/svg+xml;utf8,${encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="64" viewBox="0 0 128 64">\n      <rect width="128" height="64" fill="#f8fafc" stroke="#e5e7eb"/>\n      <g fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="10">\n        <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">preview</text>\n      </g>\n    </svg>'
  )}`;
  const categories = [
    {
      key: 'eyes',
      title: 'Eyes',
      items: [
        '/assets/Face Sketch Elements/eyes/01.png',
        '/assets/Face Sketch Elements/eyes/02.png',
        '/assets/Face Sketch Elements/eyes/03.png',
        '/assets/Face Sketch Elements/eyes/04.png',
        '/assets/Face Sketch Elements/eyes/05.png',
        '/assets/Face Sketch Elements/eyes/06.png',
        '/assets/Face Sketch Elements/eyes/07.png',
        '/assets/Face Sketch Elements/eyes/08.png',
        '/assets/Face Sketch Elements/eyes/09.png',
        '/assets/Face Sketch Elements/eyes/10.png',
        '/assets/Face Sketch Elements/eyes/11.png',
        '/assets/Face Sketch Elements/eyes/12.png',
        '/assets/Face Sketch Elements/eyes/Group 29.png',
        '/assets/Face Sketch Elements/eyes/Group 30.png',
        '/assets/Face Sketch Elements/eyes/Group 31.png',
        '/assets/Face Sketch Elements/eyes/Group 32.png',
        '/assets/Face Sketch Elements/eyes/Group 33.png',
        '/assets/Face Sketch Elements/eyes/Group 34.png',
        '/assets/Face Sketch Elements/eyes/Group 35.png',
        '/assets/Face Sketch Elements/eyes/Group 36.png',
        '/assets/Face Sketch Elements/eyes/Group 37.png',
        '/assets/Face Sketch Elements/eyes/Group 38.png',
        '/assets/Face Sketch Elements/eyes/Group 39.png',
        '/assets/Face Sketch Elements/eyes/Group 40.png'
      ]
    },
    {
      key: 'nose',
      title: 'Nose',
      items: [
        '/assets/Face Sketch Elements/nose/01.png',
        '/assets/Face Sketch Elements/nose/02.png',
        '/assets/Face Sketch Elements/nose/03.png',
        '/assets/Face Sketch Elements/nose/04.png',
        '/assets/Face Sketch Elements/nose/05.png',
        '/assets/Face Sketch Elements/nose/06.png',
        '/assets/Face Sketch Elements/nose/07.png',
        '/assets/Face Sketch Elements/nose/08.png',
        '/assets/Face Sketch Elements/nose/09.png',
        '/assets/Face Sketch Elements/nose/10.png',
        '/assets/Face Sketch Elements/nose/11.png',
        '/assets/Face Sketch Elements/nose/12.png',
        '/assets/Face Sketch Elements/nose/Group 53.png',
        '/assets/Face Sketch Elements/nose/Group 54.png',
        '/assets/Face Sketch Elements/nose/Group 55.png',
        '/assets/Face Sketch Elements/nose/Group 56.png',
        '/assets/Face Sketch Elements/nose/Group 57.png',
        '/assets/Face Sketch Elements/nose/Group 58.png',
        '/assets/Face Sketch Elements/nose/Group 59.png',
        '/assets/Face Sketch Elements/nose/Group 60.png',
        '/assets/Face Sketch Elements/nose/Group 61.png',
        '/assets/Face Sketch Elements/nose/Group 62.png',
        '/assets/Face Sketch Elements/nose/Group 63.png',
        '/assets/Face Sketch Elements/nose/Group 64.png'
      ]
    },
    {
      key: 'lips',
      title: 'Lips',
      items: [
        '/assets/Face Sketch Elements/lips/01.png',
        '/assets/Face Sketch Elements/lips/02.png',
        '/assets/Face Sketch Elements/lips/03.png',
        '/assets/Face Sketch Elements/lips/04.png',
        '/assets/Face Sketch Elements/lips/05.png',
        '/assets/Face Sketch Elements/lips/06.png',
        '/assets/Face Sketch Elements/lips/07.png',
        '/assets/Face Sketch Elements/lips/08.png',
        '/assets/Face Sketch Elements/lips/09.png',
        '/assets/Face Sketch Elements/lips/10.png',
        '/assets/Face Sketch Elements/lips/11.png',
        '/assets/Face Sketch Elements/lips/12.png',
        '/assets/Face Sketch Elements/lips/Group 65.png',
        '/assets/Face Sketch Elements/lips/Group 66.png',
        '/assets/Face Sketch Elements/lips/Group 67.png',
        '/assets/Face Sketch Elements/lips/Group 68.png',
        '/assets/Face Sketch Elements/lips/Group 69.png',
        '/assets/Face Sketch Elements/lips/Group 70.png',
        '/assets/Face Sketch Elements/lips/Group 71.png',
        '/assets/Face Sketch Elements/lips/Group 72.png',
        '/assets/Face Sketch Elements/lips/Group 73.png',
        '/assets/Face Sketch Elements/lips/Group 74.png',
        '/assets/Face Sketch Elements/lips/Group 75.png',
        '/assets/Face Sketch Elements/lips/Group 76.png'
      ]
    },
    {
      key: 'eyebrows',
      title: 'Eyebrows',
      items: [
        '/assets/Face Sketch Elements/eyebrows/01.png',
        '/assets/Face Sketch Elements/eyebrows/02.png',
        '/assets/Face Sketch Elements/eyebrows/03.png',
        '/assets/Face Sketch Elements/eyebrows/04.png',
        '/assets/Face Sketch Elements/eyebrows/05.png',
        '/assets/Face Sketch Elements/eyebrows/06.png',
        '/assets/Face Sketch Elements/eyebrows/07.png',
        '/assets/Face Sketch Elements/eyebrows/08.png',
        '/assets/Face Sketch Elements/eyebrows/09.png',
        '/assets/Face Sketch Elements/eyebrows/10.png',
        '/assets/Face Sketch Elements/eyebrows/11.png',
        '/assets/Face Sketch Elements/eyebrows/12.png',
        '/assets/Face Sketch Elements/eyebrows/Group 41.png',
        '/assets/Face Sketch Elements/eyebrows/Group 42.png',
        '/assets/Face Sketch Elements/eyebrows/Group 43.png',
        '/assets/Face Sketch Elements/eyebrows/Group 44.png',
        '/assets/Face Sketch Elements/eyebrows/Group 45.png',
        '/assets/Face Sketch Elements/eyebrows/Group 46.png',
        '/assets/Face Sketch Elements/eyebrows/Group 47.png',
        '/assets/Face Sketch Elements/eyebrows/Group 48.png',
        '/assets/Face Sketch Elements/eyebrows/Group 49.png',
        '/assets/Face Sketch Elements/eyebrows/Group 50.png',
        '/assets/Face Sketch Elements/eyebrows/Group 51.png',
        '/assets/Face Sketch Elements/eyebrows/Group 52.png'
      ]
    },
    {
      key: 'hair',
      title: 'Hair',
      items: [
        '/assets/Face Sketch Elements/hair/01.png',
        '/assets/Face Sketch Elements/hair/02.png',
        '/assets/Face Sketch Elements/hair/03.png',
        '/assets/Face Sketch Elements/hair/04.png',
        '/assets/Face Sketch Elements/hair/05.png',
        '/assets/Face Sketch Elements/hair/06.png',
        '/assets/Face Sketch Elements/hair/07.png',
        '/assets/Face Sketch Elements/hair/08.png',
        '/assets/Face Sketch Elements/hair/09.png',
        '/assets/Face Sketch Elements/hair/10.png',
        '/assets/Face Sketch Elements/hair/11.png',
        '/assets/Face Sketch Elements/hair/12.png',
        '/assets/Face Sketch Elements/hair/Group 17.png',
        '/assets/Face Sketch Elements/hair/Group 18.png',
        '/assets/Face Sketch Elements/hair/Group 19.png',
        '/assets/Face Sketch Elements/hair/Group 20.png',
        '/assets/Face Sketch Elements/hair/Group 21.png',
        '/assets/Face Sketch Elements/hair/Group 22.png',
        '/assets/Face Sketch Elements/hair/Group 23.png',
        '/assets/Face Sketch Elements/hair/Group 24.png',
        '/assets/Face Sketch Elements/hair/Group 25.png',
        '/assets/Face Sketch Elements/hair/Group 26.png',
        '/assets/Face Sketch Elements/hair/Group 27.png',
        '/assets/Face Sketch Elements/hair/Group 28.png'
      ]
    },
    {
      key: 'head',
      title: 'Head',
      items: [
        '/assets/Face Sketch Elements/head/01.png',
        '/assets/Face Sketch Elements/head/02.png',
        '/assets/Face Sketch Elements/head/03.png',
        '/assets/Face Sketch Elements/head/04.png',
        '/assets/Face Sketch Elements/head/05.png',
        '/assets/Face Sketch Elements/head/06.png',
        '/assets/Face Sketch Elements/head/07.png',
        '/assets/Face Sketch Elements/head/08.png',
        '/assets/Face Sketch Elements/head/09.png',
        '/assets/Face Sketch Elements/head/10.png',
        '/assets/Face Sketch Elements/head/Group 1.png',
        '/assets/Face Sketch Elements/head/Group 2.png',
        '/assets/Face Sketch Elements/head/Group 3.png',
        '/assets/Face Sketch Elements/head/Group 4.png',
        '/assets/Face Sketch Elements/head/Group 5.png',
        '/assets/Face Sketch Elements/head/Group 6.png',
        '/assets/Face Sketch Elements/head/Group 7.png',
        '/assets/Face Sketch Elements/head/Group 8.png',
        '/assets/Face Sketch Elements/head/Group 9.png',
        '/assets/Face Sketch Elements/head/Group 10.png'
      ]
    },
    {
      key: 'mustach',
      title: 'Mustache',
      items: [
        '/assets/Face Sketch Elements/mustach/01.png',
        '/assets/Face Sketch Elements/mustach/02.png',
        '/assets/Face Sketch Elements/mustach/03.png',
        '/assets/Face Sketch Elements/mustach/04.png',
        '/assets/Face Sketch Elements/mustach/05.png',
        '/assets/Face Sketch Elements/mustach/06.png',
        '/assets/Face Sketch Elements/mustach/07.png',
        '/assets/Face Sketch Elements/mustach/08.png',
        '/assets/Face Sketch Elements/mustach/09.png',
        '/assets/Face Sketch Elements/mustach/10.png',
        '/assets/Face Sketch Elements/mustach/11.png',
        '/assets/Face Sketch Elements/mustach/12.png',
        '/assets/Face Sketch Elements/mustach/Group 77.png',
        '/assets/Face Sketch Elements/mustach/Group 78.png',
        '/assets/Face Sketch Elements/mustach/Group 79.png',
        '/assets/Face Sketch Elements/mustach/Group 80.png',
        '/assets/Face Sketch Elements/mustach/Group 81.png',
        '/assets/Face Sketch Elements/mustach/Group 82.png',
        '/assets/Face Sketch Elements/mustach/Group 83.png',
        '/assets/Face Sketch Elements/mustach/Group 84.png',
        '/assets/Face Sketch Elements/mustach/Group 85.png',
        '/assets/Face Sketch Elements/mustach/Group 86.png',
        '/assets/Face Sketch Elements/mustach/Group 87.png',
        '/assets/Face Sketch Elements/mustach/Group 88.png'
      ]
    },
    {
      key: 'more',
      title: 'More',
      items: [
        '/assets/Face Sketch Elements/more/01.png',
        '/assets/Face Sketch Elements/more/02.png',
        '/assets/Face Sketch Elements/more/03.png',
        '/assets/Face Sketch Elements/more/04.png',
        '/assets/Face Sketch Elements/more/05.png',
        '/assets/Face Sketch Elements/more/06.png',
        '/assets/Face Sketch Elements/more/Group 11.png',
        '/assets/Face Sketch Elements/more/Group 12.png',
        '/assets/Face Sketch Elements/more/Group 13.png',
        '/assets/Face Sketch Elements/more/Group 14.png',
        '/assets/Face Sketch Elements/more/Group 15.png',
        '/assets/Face Sketch Elements/more/Group 16.png'
      ]
    }
  ];

  const [activeKey, setActiveKey] = React.useState(categories[0].key);

  const tabsStyle = {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap'
  };

  const tabBtn = (active) => ({
    padding: '8px 12px',
    border: '1px solid #cbd5e1',
    borderRadius: '6px',
    background: active ? '#111827' : '#fff',
    color: active ? '#fff' : '#111827',
    cursor: 'pointer',
    fontSize: '12px',
    whiteSpace: 'nowrap',
    minWidth: 'fit-content'
  });

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    marginBottom: '16px',
    flex: 1,
    overflowY: 'auto',
    paddingRight: '8px',
    width: '100%',
    boxSizing: 'border-box',
    alignContent: 'start',
    minHeight: 0
  };

  const imgStyle = {
    width: '100%',
    height: '80px',
    objectFit: 'contain',
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    cursor: 'pointer',
    boxSizing: 'border-box',
    maxWidth: '100%'
  };

  const active = categories.find((c) => c.key === activeKey) || categories[0];

  const containerStyle = {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    minHeight: 0,
    color: '#111827',
    overflow: 'hidden'
  };

  return (
    <div style={containerStyle}>
      <div style={tabsStyle}>
        {categories.map((cat) => (
          <button key={cat.key} style={tabBtn(activeKey === cat.key)} onClick={() => setActiveKey(cat.key)}>
            {cat.title}
          </button>
        ))}
      </div>
      <div style={gridStyle}>
        {active.items.map((src, index) => (
          <img
            key={`${active.key}-${index}`}
            src={src}
            alt={`${active.title} ${index + 1}`}
            style={imgStyle}
            onClick={() => onSelectComponent && onSelectComponent(src)}
            onError={(e) => {
              e.currentTarget.src = placeholderSvg;
              e.currentTarget.onerror = null;
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default ComponentLibrary;