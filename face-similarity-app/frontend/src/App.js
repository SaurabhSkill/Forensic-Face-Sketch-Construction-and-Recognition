import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [sketchFile, setSketchFile] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [similarityScore, setSimilarityScore] = useState(null);
  const [verified, setVerified] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Criminal database states
  const [criminals, setCriminals] = useState([]);
  const [criminalMatches, setCriminalMatches] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('compare'); // 'compare', 'criminals', 'search'
  
  // Add criminal states
  const [newCriminal, setNewCriminal] = useState({
    name: '',
    crime: '',
    description: '',
    photo: null
  });

  const handleSketchChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSketchFile(e.target.files[0]);
    }
  };

  const handlePhotoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPhotoFile(e.target.files[0]);
    }
  };

  const handleCompare = async () => {
    try {
      if (!sketchFile || !photoFile) {
        alert('Please select both a sketch and a photo.');
        return;
      }
      setLoading(true);

      const formData = new FormData();
      formData.append('sketch', sketchFile);
      formData.append('photo', photoFile);

      const response = await axios.post('http://localhost:5001/api/compare', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response && response.data && typeof response.data.distance === 'number') {
        setSimilarityScore(response.data.distance);
        if (typeof response.data.verified === 'boolean') {
          setVerified(response.data.verified);
        }
      } else {
        alert('Unexpected response from server.');
      }
    } catch (error) {
      console.error('Compare error:', error);
      alert('Failed to compare faces. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  // Criminal database functions
  const loadCriminals = async () => {
    try {
      const response = await axios.get('http://localhost:5001/api/criminals');
      setCriminals(response.data.criminals || []);
    } catch (error) {
      console.error('Error loading criminals:', error);
      alert('Failed to load criminals database.');
    }
  };

  const addCriminal = async () => {
    try {
      if (!newCriminal.photo || !newCriminal.name || !newCriminal.crime) {
        alert('Please fill in all required fields and select a photo.');
        return;
      }

      const formData = new FormData();
      formData.append('photo', newCriminal.photo);
      formData.append('name', newCriminal.name);
      formData.append('crime', newCriminal.crime);
      formData.append('description', newCriminal.description);

      const response = await axios.post('http://localhost:5001/api/criminals', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.message) {
        alert('Criminal added successfully!');
        setNewCriminal({ name: '', crime: '', description: '', photo: null });
        loadCriminals(); // Reload the list
      }
    } catch (error) {
      console.error('Error adding criminal:', error);
      alert('Failed to add criminal. Check console for details.');
    }
  };

  const searchCriminals = async () => {
    try {
      if (!sketchFile) {
        alert('Please select a sketch to search.');
        return;
      }
      setSearchLoading(true);

      const formData = new FormData();
      formData.append('sketch', sketchFile);
      formData.append('threshold', '0.6'); // Similarity threshold

      const response = await axios.post('http://localhost:5001/api/criminals/search', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data) {
        setCriminalMatches(response.data.matches || []);
        setActiveTab('search');
      }
    } catch (error) {
      console.error('Error searching criminals:', error);
      alert('Failed to search criminals. Check console for details.');
    } finally {
      setSearchLoading(false);
    }
  };

  const deleteCriminal = async (criminalId) => {
    try {
      if (window.confirm('Are you sure you want to delete this criminal?')) {
        await axios.delete(`http://localhost:5001/api/criminals/${criminalId}`);
        alert('Criminal deleted successfully!');
        loadCriminals(); // Reload the list
      }
    } catch (error) {
      console.error('Error deleting criminal:', error);
      alert('Failed to delete criminal. Check console for details.');
    }
  };

  // Load criminals on component mount
  React.useEffect(() => {
    loadCriminals();
  }, []);


  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="logo">
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <div className="logo-text">
              <span className="logo-main">FaceFind</span>
              <span className="logo-sub">Forensics</span>
            </div>
          </div>
          <nav className="nav">
            <button 
              className={`nav-link ${activeTab === 'compare' ? 'active' : ''}`}
              onClick={() => setActiveTab('compare')}
            >
              Face Comparison
            </button>
            <button 
              className={`nav-link ${activeTab === 'criminals' ? 'active' : ''}`}
              onClick={() => setActiveTab('criminals')}
            >
              Criminal Database
            </button>
            <button 
              className={`nav-link ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              Sketch Search
            </button>
            <a href="#about" className="nav-link">About Us</a>
            <a href="#contact" className="nav-link">Contact</a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero-content">
            <div className="hero-visual">
              <div className="tablet-mockup">
                <div className="tablet-screen">
                  <div className="sketch-preview">
                    <div className="sketch-half sketch-detailed"></div>
                    <div className="sketch-half sketch-outline"></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="hero-text">
              <h1 className="hero-title">Unlocking Identities Through Advanced Facial Reconstruction</h1>
              <p className="hero-subtitle">Bridging the Gap Between Testimony and Positive Identification</p>
              <button className="cta-button">START A SKETCH</button>
            </div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section className="services">
        <div className="container">
          <h2 className="section-title">Services</h2>
          <div className="services-grid">
            <div className="service-card">
              <div className="service-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3>Digital Sketching</h3>
            </div>
            <div className="service-card">
              <div className="service-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <h3>Database Matching</h3>
              <div className="progress-bar"></div>
            </div>
            <div className="service-card">
              <div className="service-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                </svg>
              </div>
              <h3>Expert Analysis</h3>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works">
        <div className="container">
          <h2 className="section-title">How It Works</h2>
          <div className="process-flow">
            <div className="process-step">
              <div className="step-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <h3>Witness Interview</h3>
            </div>
            <div className="process-connector"></div>
            <div className="process-step">
              <div className="step-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3>Sketch Creation</h3>
            </div>
            <div className="process-connector"></div>
            <div className="process-step">
              <div className="step-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>
                </svg>
              </div>
              <h3>Recognition Process</h3>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Section */}
      <section className="main-content">
        <div className="container">
          {/* Face Comparison Tab */}
          {activeTab === 'compare' && (
            <div className="tab-content">
              <h2 className="section-title">Facial Recognition Tool</h2>
              <div className="comparison-container">
                <div className="upload-section">
                  <div className="upload-area">
                    <h3>Upload Sketch</h3>
                    <input 
                      type="file" 
                      accept="image/*" 
                      onChange={handleSketchChange}
                      className="file-input"
                      id="sketch-upload"
                    />
                    <label htmlFor="sketch-upload" className="file-label">
                      {sketchFile ? sketchFile.name : 'Choose Sketch File'}
                    </label>
                  </div>
                  <div className="upload-area">
                    <h3>Upload Photo</h3>
                    <input 
                      type="file" 
                      accept="image/*" 
                      onChange={handlePhotoChange}
                      className="file-input"
                      id="photo-upload"
                    />
                    <label htmlFor="photo-upload" className="file-label">
                      {photoFile ? photoFile.name : 'Choose Photo File'}
                    </label>
                  </div>
                </div>
                
                <button
                  className="compare-button"
                  onClick={handleCompare}
                  disabled={!sketchFile || !photoFile || loading}
                >
                  {loading ? 'Analyzing...' : 'Compare Faces'}
                </button>

                {similarityScore !== null && (
                  <div className="results">
                    <div className="result-card">
                      <h3>Analysis Results</h3>
                      <div className="result-metrics">
                        <div className="metric">
                          <span className="metric-label">Similarity Score:</span>
                          <span className="metric-value">{similarityScore.toFixed(4)}</span>
                        </div>
                        <div className="metric">
                          <span className="metric-label">Verification:</span>
                          <span className={`metric-value ${verified ? 'match' : 'no-match'}`}>
                            {verified ? 'Match' : 'No Match'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Criminal Database Tab */}
          {activeTab === 'criminals' && (
            <div className="tab-content">
              <h2 className="section-title">Criminal Database Management</h2>
              
              {/* Add Criminal Form */}
              <div className="add-criminal-form">
                <h3>Add New Criminal</h3>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Name *</label>
                    <input
                      type="text"
                      value={newCriminal.name}
                      onChange={(e) => setNewCriminal({...newCriminal, name: e.target.value})}
                      placeholder="Enter criminal name"
                    />
                  </div>
                  <div className="form-group">
                    <label>Crime *</label>
                    <input
                      type="text"
                      value={newCriminal.crime}
                      onChange={(e) => setNewCriminal({...newCriminal, crime: e.target.value})}
                      placeholder="Enter crime committed"
                    />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <textarea
                      value={newCriminal.description}
                      onChange={(e) => setNewCriminal({...newCriminal, description: e.target.value})}
                      placeholder="Additional details"
                      rows="3"
                    />
                  </div>
                  <div className="form-group">
                    <label>Photo *</label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setNewCriminal({...newCriminal, photo: e.target.files[0]})}
                      className="file-input"
                      id="criminal-photo"
                    />
                    <label htmlFor="criminal-photo" className="file-label">
                      {newCriminal.photo ? newCriminal.photo.name : 'Choose Photo'}
                    </label>
                  </div>
                </div>
                <button className="add-button" onClick={addCriminal}>
                  Add Criminal
                </button>
              </div>

              {/* Criminals List */}
              <div className="criminals-list">
                <h3>Criminals in Database ({criminals.length})</h3>
                <div className="criminals-grid">
                  {criminals.map((criminal) => (
                    <div key={criminal.id} className="criminal-card">
                      <div className="criminal-image">
                        <img 
                          src={`http://localhost:5001/api/criminals/${criminal.id}/photo`}
                          alt={criminal.name}
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                        <div className="image-placeholder" style={{display: 'none'}}>
                          <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
                          </svg>
                        </div>
                      </div>
                      <div className="criminal-info">
                        <h4>{criminal.name}</h4>
                        <p className="crime">{criminal.crime}</p>
                        {criminal.description && <p className="description">{criminal.description}</p>}
                        <p className="date">Added: {new Date(criminal.created_at).toLocaleDateString()}</p>
                      </div>
                      <button 
                        className="delete-button"
                        onClick={() => deleteCriminal(criminal.id)}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Sketch Search Tab */}
          {activeTab === 'search' && (
            <div className="tab-content">
              <h2 className="section-title">Sketch Search</h2>
              <div className="search-container">
                <div className="upload-section">
                  <div className="upload-area">
                    <h3>Upload Sketch to Search</h3>
                    <input 
                      type="file" 
                      accept="image/*" 
                      onChange={handleSketchChange}
                      className="file-input"
                      id="search-sketch-upload"
                    />
                    <label htmlFor="search-sketch-upload" className="file-label">
                      {sketchFile ? sketchFile.name : 'Choose Sketch File'}
                    </label>
                  </div>
                </div>
                
                <button
                  className="search-button"
                  onClick={searchCriminals}
                  disabled={!sketchFile || searchLoading}
                >
                  {searchLoading ? 'Searching...' : 'Search Criminals'}
                </button>

                {/* Search Results */}
                {criminalMatches.length > 0 && (
                  <div className="search-results">
                    <h3>Search Results ({criminalMatches.length} matches found)</h3>
                    <div className="matches-grid">
                      {criminalMatches.map((match, index) => (
                        <div key={match.criminal.id} className="match-card">
                          <div className="match-image">
                            <img 
                              src={`http://localhost:5001/api/criminals/${match.criminal.id}/photo`}
                              alt={match.criminal.name}
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'flex';
                              }}
                            />
                            <div className="image-placeholder" style={{display: 'none'}}>
                              <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
                              </svg>
                            </div>
                          </div>
                          <div className="match-info">
                            <h4>{match.criminal.name}</h4>
                            <p className="crime">{match.criminal.crime}</p>
                            {match.criminal.description && <p className="description">{match.criminal.description}</p>}
                            <div className="similarity-score">
                              <span className="score-label">Match Score:</span>
                              <span className="score-value">{(match.similarity_score * 100).toFixed(1)}%</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {criminalMatches.length === 0 && searchLoading === false && (
                  <div className="no-matches">
                    <div className="no-matches-content">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                      </svg>
                      <h3>No Criminals Found</h3>
                      <p>There are no criminals like this in our database.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-contact">
              <div className="contact-item">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z"/>
                </svg>
                <span>+05 231 958</span>
              </div>
              <div className="contact-item">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V6C22,4.89 21.1,4 20,4M20,8L12,13L4,8V6L12,11L20,6V8Z"/>
                </svg>
                <span>FaceFindPro.com</span>
              </div>
            </div>
            <div className="footer-links">
              <a href="#" className="footer-link">NonSlotom</a>
              <a href="#" className="footer-link">Facenlotiom</a>
              <a href="#" className="footer-link">Forensic Fecition Faceminuics.com</a>
            </div>
            <div className="footer-decoration">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,2L13.09,8.26L22,9L17,14L18.18,22L12,18.77L5.82,22L7,14L2,9L10.91,8.26L12,2Z"/>
              </svg>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
