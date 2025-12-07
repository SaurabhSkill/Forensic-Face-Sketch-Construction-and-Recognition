import React, { useState } from 'react';
import './AddCriminalForm.css';

const AddCriminalForm = ({ onSubmit, onCancel }) => {
  const [activeTab, setActiveTab] = useState('basic');
  const [photoPreview, setPhotoPreview] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    // Basic Info
    criminal_id: '',
    status: 'Person of Interest',
    full_name: '',
    aliases: [],
    dob: '',
    sex: '',
    nationality: '',
    ethnicity: '',
    photo: null,
    
    // Appearance
    appearance: {
      height: '',
      weight: '',
      build: '',
      hair: '',
      eyes: '',
      marks: [],
      tattoos: '',
      scars: ''
    },
    
    // Locations
    locations: {
      city: '',
      state: '',
      country: '',
      lastSeen: '',
      knownAddresses: []
    },
    
    // Summary
    summary: {
      charges: '',
      modus: '',
      risk: 'Low',
      priorConvictions: 0
    },
    
    // Forensics
    forensics: {
      fingerprintId: '',
      dnaProfile: '',
      gait: '',
      voiceprint: ''
    },
    
    // Evidence
    evidence: [],
    
    // Witness
    witness: {
      statements: '',
      credibility: 'Medium',
      contactInfo: ''
    }
  });

  // Temporary input states for arrays
  const [newAlias, setNewAlias] = useState('');
  const [newMark, setNewMark] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [newEvidence, setNewEvidence] = useState('');

  // Handle basic field changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle nested object changes
  const handleNestedChange = (section, field, value) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  // Handle photo upload
  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, photo: file }));
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Array management functions
  const addAlias = () => {
    if (newAlias.trim()) {
      setFormData(prev => ({
        ...prev,
        aliases: [...prev.aliases, newAlias.trim()]
      }));
      setNewAlias('');
    }
  };

  const removeAlias = (index) => {
    setFormData(prev => ({
      ...prev,
      aliases: prev.aliases.filter((_, i) => i !== index)
    }));
  };

  const addMark = () => {
    if (newMark.trim()) {
      setFormData(prev => ({
        ...prev,
        appearance: {
          ...prev.appearance,
          marks: [...prev.appearance.marks, newMark.trim()]
        }
      }));
      setNewMark('');
    }
  };

  const removeMark = (index) => {
    setFormData(prev => ({
      ...prev,
      appearance: {
        ...prev.appearance,
        marks: prev.appearance.marks.filter((_, i) => i !== index)
      }
    }));
  };

  const addAddress = () => {
    if (newAddress.trim()) {
      setFormData(prev => ({
        ...prev,
        locations: {
          ...prev.locations,
          knownAddresses: [...prev.locations.knownAddresses, newAddress.trim()]
        }
      }));
      setNewAddress('');
    }
  };

  const removeAddress = (index) => {
    setFormData(prev => ({
      ...prev,
      locations: {
        ...prev.locations,
        knownAddresses: prev.locations.knownAddresses.filter((_, i) => i !== index)
      }
    }));
  };

  const addEvidence = () => {
    if (newEvidence.trim()) {
      setFormData(prev => ({
        ...prev,
        evidence: [...prev.evidence, newEvidence.trim()]
      }));
      setNewEvidence('');
    }
  };

  const removeEvidence = (index) => {
    setFormData(prev => ({
      ...prev,
      evidence: prev.evidence.filter((_, i) => i !== index)
    }));
  };

  // Form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formData.criminal_id || !formData.full_name || !formData.photo) {
      alert('Please fill in Criminal ID, Full Name, and upload a photo.');
      return;
    }
    
    onSubmit(formData);
  };

  return (
    <div className="add-criminal-form-overlay">
      <div className="add-criminal-form-container">
        <div className="form-header">
          <h2>Add New Criminal Profile</h2>
          <button className="close-button" onClick={onCancel}>×</button>
        </div>

        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button
            className={`tab-button ${activeTab === 'basic' ? 'active' : ''}`}
            onClick={() => setActiveTab('basic')}
          >
            Basic Info
          </button>
          <button
            className={`tab-button ${activeTab === 'appearance' ? 'active' : ''}`}
            onClick={() => setActiveTab('appearance')}
          >
            Appearance
          </button>
          <button
            className={`tab-button ${activeTab === 'location' ? 'active' : ''}`}
            onClick={() => setActiveTab('location')}
          >
            Location & History
          </button>
          <button
            className={`tab-button ${activeTab === 'forensics' ? 'active' : ''}`}
            onClick={() => setActiveTab('forensics')}
          >
            Forensics & Evidence
          </button>
        </div>

        <form onSubmit={handleSubmit} className="criminal-form">
          {/* Tab 1: Basic Info */}
          {activeTab === 'basic' && (
            <div className="tab-content">
              <h3>Basic Information</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Criminal ID *</label>
                  <input
                    type="text"
                    name="criminal_id"
                    value={formData.criminal_id}
                    onChange={handleChange}
                    placeholder="e.g., CR-0001-TST"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Status *</label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                    required
                  >
                    <option value="Person of Interest">Person of Interest</option>
                    <option value="Suspect">Suspect</option>
                    <option value="Wanted">Wanted</option>
                    <option value="Convicted">Convicted</option>
                    <option value="Released">Released</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  placeholder="Enter full name"
                  required
                />
              </div>

              <div className="form-group">
                <label>Aliases / Known As</label>
                <div className="array-input-group">
                  <input
                    type="text"
                    value={newAlias}
                    onChange={(e) => setNewAlias(e.target.value)}
                    placeholder="Enter alias"
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addAlias())}
                  />
                  <button type="button" onClick={addAlias} className="add-button">
                    + Add
                  </button>
                </div>
                <div className="array-items">
                  {formData.aliases.map((alias, index) => (
                    <span key={index} className="array-item">
                      {alias}
                      <button type="button" onClick={() => removeAlias(index)}>×</button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Date of Birth</label>
                  <input
                    type="date"
                    name="dob"
                    value={formData.dob}
                    onChange={handleChange}
                  />
                </div>
                
                <div className="form-group">
                  <label>Sex</label>
                  <select
                    name="sex"
                    value={formData.sex}
                    onChange={handleChange}
                  >
                    <option value="">Select</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nationality</label>
                  <input
                    type="text"
                    name="nationality"
                    value={formData.nationality}
                    onChange={handleChange}
                    placeholder="e.g., American"
                  />
                </div>
                
                <div className="form-group">
                  <label>Ethnicity</label>
                  <input
                    type="text"
                    name="ethnicity"
                    value={formData.ethnicity}
                    onChange={handleChange}
                    placeholder="e.g., Caucasian"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Photo *</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  className="file-input"
                  id="photo-upload"
                  required
                />
                <label htmlFor="photo-upload" className="file-label">
                  {formData.photo ? formData.photo.name : 'Choose Photo'}
                </label>
                {photoPreview && (
                  <div className="photo-preview">
                    <img src={photoPreview} alt="Preview" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 2: Appearance */}
          {activeTab === 'appearance' && (
            <div className="tab-content">
              <h3>Physical Appearance</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Height</label>
                  <input
                    type="text"
                    value={formData.appearance.height}
                    onChange={(e) => handleNestedChange('appearance', 'height', e.target.value)}
                    placeholder="e.g., 6'2&quot;"
                  />
                </div>
                
                <div className="form-group">
                  <label>Weight</label>
                  <input
                    type="text"
                    value={formData.appearance.weight}
                    onChange={(e) => handleNestedChange('appearance', 'weight', e.target.value)}
                    placeholder="e.g., 180 lbs"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Build</label>
                  <select
                    value={formData.appearance.build}
                    onChange={(e) => handleNestedChange('appearance', 'build', e.target.value)}
                  >
                    <option value="">Select</option>
                    <option value="Slim">Slim</option>
                    <option value="Athletic">Athletic</option>
                    <option value="Average">Average</option>
                    <option value="Muscular">Muscular</option>
                    <option value="Heavy">Heavy</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Hair Color</label>
                  <input
                    type="text"
                    value={formData.appearance.hair}
                    onChange={(e) => handleNestedChange('appearance', 'hair', e.target.value)}
                    placeholder="e.g., Brown"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Eye Color</label>
                <input
                  type="text"
                  value={formData.appearance.eyes}
                  onChange={(e) => handleNestedChange('appearance', 'eyes', e.target.value)}
                  placeholder="e.g., Blue"
                />
              </div>

              <div className="form-group">
                <label>Distinguishing Marks</label>
                <div className="array-input-group">
                  <input
                    type="text"
                    value={newMark}
                    onChange={(e) => setNewMark(e.target.value)}
                    placeholder="e.g., Scar on left cheek"
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addMark())}
                  />
                  <button type="button" onClick={addMark} className="add-button">
                    + Add
                  </button>
                </div>
                <div className="array-items">
                  {formData.appearance.marks.map((mark, index) => (
                    <span key={index} className="array-item">
                      {mark}
                      <button type="button" onClick={() => removeMark(index)}>×</button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Tattoos</label>
                <textarea
                  value={formData.appearance.tattoos}
                  onChange={(e) => handleNestedChange('appearance', 'tattoos', e.target.value)}
                  placeholder="Describe any tattoos"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Scars</label>
                <textarea
                  value={formData.appearance.scars}
                  onChange={(e) => handleNestedChange('appearance', 'scars', e.target.value)}
                  placeholder="Describe any scars"
                  rows="3"
                />
              </div>
            </div>
          )}

          {/* Tab 3: Location & History */}
          {activeTab === 'location' && (
            <div className="tab-content">
              <h3>Location & Criminal History</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label>City</label>
                  <input
                    type="text"
                    value={formData.locations.city}
                    onChange={(e) => handleNestedChange('locations', 'city', e.target.value)}
                    placeholder="e.g., New York"
                  />
                </div>
                
                <div className="form-group">
                  <label>State</label>
                  <input
                    type="text"
                    value={formData.locations.state}
                    onChange={(e) => handleNestedChange('locations', 'state', e.target.value)}
                    placeholder="e.g., NY"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Country</label>
                  <input
                    type="text"
                    value={formData.locations.country}
                    onChange={(e) => handleNestedChange('locations', 'country', e.target.value)}
                    placeholder="e.g., USA"
                  />
                </div>
                
                <div className="form-group">
                  <label>Last Seen</label>
                  <input
                    type="date"
                    value={formData.locations.lastSeen}
                    onChange={(e) => handleNestedChange('locations', 'lastSeen', e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Known Addresses</label>
                <div className="array-input-group">
                  <input
                    type="text"
                    value={newAddress}
                    onChange={(e) => setNewAddress(e.target.value)}
                    placeholder="Enter address"
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addAddress())}
                  />
                  <button type="button" onClick={addAddress} className="add-button">
                    + Add
                  </button>
                </div>
                <div className="array-items">
                  {formData.locations.knownAddresses.map((address, index) => (
                    <span key={index} className="array-item">
                      {address}
                      <button type="button" onClick={() => removeAddress(index)}>×</button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Charges</label>
                <input
                  type="text"
                  value={formData.summary.charges}
                  onChange={(e) => handleNestedChange('summary', 'charges', e.target.value)}
                  placeholder="e.g., Armed Robbery"
                />
              </div>

              <div className="form-group">
                <label>Modus Operandi (M.O.)</label>
                <textarea
                  value={formData.summary.modus}
                  onChange={(e) => handleNestedChange('summary', 'modus', e.target.value)}
                  placeholder="Describe criminal's typical methods"
                  rows="3"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Risk Level</label>
                  <select
                    value={formData.summary.risk}
                    onChange={(e) => handleNestedChange('summary', 'risk', e.target.value)}
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Prior Convictions</label>
                  <input
                    type="number"
                    value={formData.summary.priorConvictions}
                    onChange={(e) => handleNestedChange('summary', 'priorConvictions', parseInt(e.target.value) || 0)}
                    min="0"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: Forensics & Evidence */}
          {activeTab === 'forensics' && (
            <div className="tab-content">
              <h3>Forensic Data & Evidence</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Fingerprint ID</label>
                  <input
                    type="text"
                    value={formData.forensics.fingerprintId}
                    onChange={(e) => handleNestedChange('forensics', 'fingerprintId', e.target.value)}
                    placeholder="e.g., FP-12345"
                  />
                </div>
                
                <div className="form-group">
                  <label>DNA Profile ID</label>
                  <input
                    type="text"
                    value={formData.forensics.dnaProfile}
                    onChange={(e) => handleNestedChange('forensics', 'dnaProfile', e.target.value)}
                    placeholder="e.g., DNA-67890"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Gait Analysis</label>
                <input
                  type="text"
                  value={formData.forensics.gait}
                  onChange={(e) => handleNestedChange('forensics', 'gait', e.target.value)}
                  placeholder="e.g., Slight limp on right leg"
                />
              </div>

              <div className="form-group">
                <label>Voiceprint ID</label>
                <input
                  type="text"
                  value={formData.forensics.voiceprint}
                  onChange={(e) => handleNestedChange('forensics', 'voiceprint', e.target.value)}
                  placeholder="e.g., VP-11223"
                />
              </div>

              <div className="form-group">
                <label>Evidence Items</label>
                <div className="array-input-group">
                  <input
                    type="text"
                    value={newEvidence}
                    onChange={(e) => setNewEvidence(e.target.value)}
                    placeholder="e.g., Security footage"
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addEvidence())}
                  />
                  <button type="button" onClick={addEvidence} className="add-button">
                    + Add
                  </button>
                </div>
                <div className="array-items">
                  {formData.evidence.map((item, index) => (
                    <span key={index} className="array-item">
                      {item}
                      <button type="button" onClick={() => removeEvidence(index)}>×</button>
                    </span>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Witness Statements</label>
                <textarea
                  value={formData.witness.statements}
                  onChange={(e) => handleNestedChange('witness', 'statements', e.target.value)}
                  placeholder="Enter witness statements"
                  rows="4"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Witness Credibility</label>
                  <select
                    value={formData.witness.credibility}
                    onChange={(e) => handleNestedChange('witness', 'credibility', e.target.value)}
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Witness Contact</label>
                  <input
                    type="text"
                    value={formData.witness.contactInfo}
                    onChange={(e) => handleNestedChange('witness', 'contactInfo', e.target.value)}
                    placeholder="Email or phone"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div className="form-actions">
            <button type="button" onClick={onCancel} className="cancel-button">
              Cancel
            </button>
            <button type="submit" className="submit-button">
              Add Criminal Profile
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddCriminalForm;
