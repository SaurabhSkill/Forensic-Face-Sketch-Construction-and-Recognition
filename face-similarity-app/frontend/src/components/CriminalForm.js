import React, { useState, useRef } from 'react';

const initialState = {
  criminalId: '',
  status: '',
  fullName: '',
  aliases: [''],
  dob: '',
  estimatedAge: '',
  sex: '',
  nationality: '',
  ethnicity: '',
  photo: null,
  appearance: {
    height: '',
    weight: '',
    build: '',
    eyeColor: '',
    hair: '',
    facialHair: '',
    marks: [''],
    clothing: ''
  },
  locations: {
    city: '',
    area: '',
    lastSeen: '',
    frequent: ['']
  },
  summary: {
    charges: [''],
    modus: '',
    risk: ''
  },
  forensics: {
    fingerprintId: '',
    dnaSampleId: '',
    gait: '',
    bootTread: ''
  },
  evidence: [''],
  witness: {
    a: '',
    b: ''
  }
};

function CriminalForm() {
  const [form, setForm] = useState(initialState);
  const [preview, setPreview] = useState(false);
  const [photoURL, setPhotoURL] = useState('');
  const photoRef = useRef();

  // Top-level and nested change helpers
  const change = (f, v) => setForm({ ...form, [f]: v });
  const nested = (s, f, v) => setForm({ ...form, [s]: { ...form[s], [f]: v } });
  const arr = (s, idx, val, nest) => {
    let arr = nest ? [...form[s[0]][s[1]]] : [...form[s]];
    arr[idx] = val;
    nest
      ? setForm({ ...form, [s[0]]: { ...form[s[0]], [s[1]]: arr } })
      : setForm({ ...form, [s]: arr });
  };
  const addArr = (s, nest) => {
    let arr = nest ? [...form[s[0]][s[1]]] : [...form[s]];
    arr.push('');
    nest
      ? setForm({ ...form, [s[0]]: { ...form[s[0]], [s[1]]: arr } })
      : setForm({ ...form, [s]: arr });
  };
  const delArr = (s, idx, nest) => {
    let arr = nest ? [...form[s[0]][s[1]]] : [...form[s]];
    if (arr.length === 1) return;
    arr.splice(idx, 1);
    nest
      ? setForm({ ...form, [s[0]]: { ...form[s[0]], [s[1]]: arr } })
      : setForm({ ...form, [s]: arr });
  };

  // Photo upload handler
  const onPhoto = e => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      setPhotoURL(URL.createObjectURL(file));
      setForm({ ...form, photo: file });
    }
  };

  // Handle submit
  const onSubmit = e => {
    e.preventDefault();
    setPreview(false);
    alert(JSON.stringify({ ...form, photo: undefined }, null, 2));
    // Here, you'd send 'form' (convert photo to base64 if needed) to the backend
  };

  return (
    <div className="criminal-entry-form max-w-2xl mx-auto py-10 px-3">
      <form onSubmit={onSubmit} className="bg-white p-5 rounded-xl shadow-md space-y-7">
        {/* 1. Identity & Status section */}
        <h2 className="text-xl font-bold pb-1 border-b">Criminal Identity & Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block font-medium">Criminal ID *</label>
            <input className="w-full" required value={form.criminalId} onChange={e=>change('criminalId',e.target.value)} placeholder="CR-0001-TST" />
          </div>
          <div>
            <label className="block font-medium">Status *</label>
            <select className="w-full" required value={form.status} onChange={e=>change('status',e.target.value)}>
              <option value="">Select...</option>
              <option>Person of Interest</option>
              <option>Wanted</option>
              <option>Fugitive</option>
              <option>In Custody</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block font-medium">Full Name *</label>
            <input className="w-full" required value={form.fullName} onChange={e=>change('fullName',e.target.value)} placeholder="Aaron V. Mercer" />
          </div>
          <div>
            <label className="block font-medium">Date of Birth</label>
            <input className="w-full" type="date" value={form.dob} onChange={e=>change('dob',e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block font-medium">Estimated Age</label>
            <input className="w-full" type="number" placeholder="38" value={form.estimatedAge} onChange={e=>change('estimatedAge',e.target.value)} />
          </div>
          <div>
            <label className="block font-medium">Sex</label>
            <select className="w-full" value={form.sex} onChange={e=>change('sex',e.target.value)}>
              <option value="">Select...</option>
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </div>
          <div>
            <label className="block font-medium">Nationality</label>
            <input className="w-full" placeholder="Fictionlandian" value={form.nationality} onChange={e=>change('nationality',e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block font-medium">Ethnicity</label>
          <input className="w-full" placeholder="South Asian" value={form.ethnicity} onChange={e=>change('ethnicity',e.target.value)} />
        </div>
        <div>
          <label className="block font-medium">Known Aliases</label>
          {form.aliases.map((alias, idx) => (
            <div key={idx} className="flex gap-2 mb-1">
              <input className="flex-1" value={alias} placeholder="Red Hammer, Mercer" onChange={e=>arr('aliases',idx,e.target.value)} />
              <button type="button" onClick={()=>delArr('aliases',idx)} disabled={form.aliases.length===1}>-</button>
              {idx===form.aliases.length-1 && <button type="button" onClick={()=>addArr('aliases')}>+</button>}
            </div>
          ))}
        </div>
        {/* 2. Photo Section */}
        <h2 className="text-xl font-bold border-b pb-1">Criminal Photo</h2>
        <div>
          <input className="" type="file" accept="image/*" required ref={photoRef} onChange={onPhoto} />
          {photoURL && <div className="mt-2"><img src={photoURL} alt="Preview" className="rounded-lg w-40 h-40 object-cover border" /></div>}
        </div>
        {/* 3. Appearance Section */}
        <h2 className="text-xl font-bold border-b pb-1">Physical Description</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>Height (cm)</label>
            <input className="w-full" placeholder="180" value={form.appearance.height} onChange={e=>nested('appearance','height',e.target.value)} />
          </div>
          <div>
            <label>Weight (kg)</label>
            <input className="w-full" placeholder="82" value={form.appearance.weight} onChange={e=>nested('appearance','weight',e.target.value)} />
          </div>
          <div>
            <label>Build</label>
            <input className="w-full" placeholder="Medium-athletic" value={form.appearance.build} onChange={e=>nested('appearance','build',e.target.value)} />
          </div>
          <div>
            <label>Eye Color</label>
            <input className="w-full" placeholder="Dark Brown" value={form.appearance.eyeColor} onChange={e=>nested('appearance','eyeColor',e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>Hair</label>
            <input className="w-full" placeholder="Black, short, receding hairline" value={form.appearance.hair} onChange={e=>nested('appearance','hair',e.target.value)} />
          </div>
          <div>
            <label>Facial Hair</label>
            <input className="w-full" placeholder="Short stubble (often present)" value={form.appearance.facialHair} onChange={e=>nested('appearance','facialHair',e.target.value)} />
          </div>
        </div>
        <div>
          <label>Distinctive Marks</label>
          {form.appearance.marks.map((m, idx) => (
            <div key={idx} className="flex gap-2 mb-1">
              <input className="flex-1" placeholder="Scar on eyebrow, tattoo on forearm" value={m} onChange={e=>arr(['appearance','marks'],idx,e.target.value,true)} />
              <button type="button" onClick={()=>delArr(['appearance','marks'],idx,true)} disabled={form.appearance.marks.length===1}>-</button>
              {idx===form.appearance.marks.length-1 && <button type="button" onClick={()=>addArr(['appearance','marks'],true)}>+</button>}
            </div>
          ))}
        </div>
        <div>
          <label>Typical Clothing</label>
          <input className="w-full" placeholder="Hooded jacket, jeans, boots, etc." value={form.appearance.clothing} onChange={e=>nested('appearance','clothing',e.target.value)} />
        </div>
        {/* 4. Location Section */}
        <h2 className="text-xl font-bold border-b pb-1">Known Locations</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>City</label>
            <input className="w-full" placeholder="Westbridge" value={form.locations.city} onChange={e=>nested('locations','city',e.target.value)} />
          </div>
          <div>
            <label>Area</label>
            <input className="w-full" placeholder="Sector 7 — Downtown" value={form.locations.area} onChange={e=>nested('locations','area',e.target.value)} />
          </div>
        </div>
        <div>
          <label>Last Seen (Date & Time)</label>
          <input type="datetime-local" className="w-full" value={form.locations.lastSeen} onChange={e=>nested('locations','lastSeen',e.target.value)} />
        </div>
        <div>
          <label>Frequent Locations</label>
          {form.locations.frequent.map((loc, idx)=> (
            <div key={idx} className="flex gap-2 mb-1">
              <input className="flex-1" placeholder="The Iron Dock Bar" value={loc} onChange={e=>arr(['locations','frequent'],idx,e.target.value,true)} />
              <button type="button" onClick={()=>delArr(['locations','frequent'],idx,true)} disabled={form.locations.frequent.length===1}>-</button>
              {idx===form.locations.frequent.length-1 && <button type="button" onClick={()=>addArr(['locations','frequent'],true)}>+</button>}
            </div>
          ))}
        </div>
        {/* 5. Summary Section */}
        <h2 className="text-xl font-bold border-b pb-1">Criminal Summary</h2>
        <div>
          <label>Known Charges</label>
          {form.summary.charges.map((c, idx)=> (
            <div key={idx} className="flex gap-2 mb-1">
              <input className="flex-1" placeholder="Aggravated burglary, Conspiracy..." value={c} onChange={e=>arr(['summary','charges'],idx,e.target.value,true)} />
              <button type="button" onClick={()=>delArr(['summary','charges'],idx,true)} disabled={form.summary.charges.length===1}>-</button>
              {idx===form.summary.charges.length-1 && <button type="button" onClick={()=>addArr(['summary','charges'],true)}>+</button>}
            </div>
          ))}
        </div>
        <div>
          <label>Modus Operandi</label>
          <textarea className="w-full" rows={2} placeholder="Night-time break-ins, disables CCTV..." value={form.summary.modus} onChange={e=>nested('summary','modus',e.target.value)} />
        </div>
        <div>
          <label>Risk Level</label>
          <select className="w-full" value={form.summary.risk} onChange={e=>nested('summary','risk',e.target.value)}>
            <option value="">Select...</option>
            <option>Low</option>
            <option>Moderate</option>
            <option>High</option>
            <option>Extreme</option>
          </select>
        </div>
        {/* 6. Forensics Section */}
        <h2 className="text-xl font-bold border-b pb-1">Forensic Identifiers</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>Fingerprint ID</label>
            <input className="w-full" placeholder="FP-TST-0001" value={form.forensics.fingerprintId} onChange={e=>nested('forensics','fingerprintId',e.target.value)} />
          </div>
          <div>
            <label>DNA Sample ID</label>
            <input className="w-full" placeholder="DNA-TST-0001" value={form.forensics.dnaSampleId} onChange={e=>nested('forensics','dnaSampleId',e.target.value)} />
          </div>
          <div>
            <label>Gait Observation</label>
            <input className="w-full" placeholder="Slight limp, etc." value={form.forensics.gait} onChange={e=>nested('forensics','gait',e.target.value)} />
          </div>
          <div>
            <label>Boot Tread Pattern</label>
            <input className="w-full" placeholder="M-120 Workboot" value={form.forensics.bootTread} onChange={e=>nested('forensics','bootTread',e.target.value)} />
          </div>
        </div>
        {/* 7. Evidence Section */}
        <h2 className="text-xl font-bold border-b pb-1">Evidence References</h2>
        {form.evidence.map((ref, idx) => (
          <div key={idx} className="flex gap-2 mb-1">
            <input className="flex-1" placeholder="EI-001, EI-002, ..." value={ref} onChange={e=>arr('evidence',idx,e.target.value)} />
            <button type="button" onClick={()=>delArr('evidence',idx)} disabled={form.evidence.length===1}>-</button>
            {idx===form.evidence.length-1 && <button type="button" onClick={()=>addArr('evidence')}>+</button>}
          </div>
        ))}
        {/* 8. Witness Section */}
        <h2 className="text-xl font-bold border-b pb-1">Witness Statements</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label>Witness A</label>
            <textarea className="w-full" rows={2} placeholder="Testimony..." value={form.witness.a} onChange={e=>nested('witness','a',e.target.value)} />
          </div>
          <div>
            <label>Witness B</label>
            <textarea className="w-full" rows={2} placeholder="Testimony..." value={form.witness.b} onChange={e=>nested('witness','b',e.target.value)} />
          </div>
        </div>
        {/* 9. Actions */}
        <div className="pt-5 flex gap-2">
          <button type="submit" className="rounded bg-blue-700 px-8 py-2 text-white font-bold">Submit</button>
          <button type="button" className="rounded bg-gray-200 px-6 py-2 font-semibold" onClick={()=>setPreview(!preview)}>{preview ? 'Hide Preview' : 'Preview JSON'}</button>
        </div>
      </form>
      {preview && (
        <div className="bg-slate-900 text-gray-100 text-sm mt-8 p-4 rounded-xl whitespace-pre-wrap">
          <h3 className="font-bold mb-2">Record JSON Preview</h3>
          <pre>{JSON.stringify({ ...form, photo: undefined }, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default CriminalForm;
