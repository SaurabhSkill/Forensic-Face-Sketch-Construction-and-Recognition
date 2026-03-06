import React, { useState, useEffect } from 'react';
import CriminalList from '../components/CriminalList';
import AddCriminalForm from '../components/AddCriminalForm';
import { apiService } from '../services/apiService';
import PageContainer from '../layout/PageContainer';

const DatabasePage = () => {
  const [criminals, setCriminals] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);

  const loadCriminals = async () => {
    try {
      const data = await apiService.getCriminals();
      setCriminals(data);
    } catch (error) {
      console.error('Error loading criminals:', error);
      
      if (error.response && error.response.status === 401) {
        return;
      }
      
      let errorMessage = 'Failed to load criminals database. ';
      
      if (error.code === 'ECONNREFUSED' || error.message.includes('ERR_CONNECTION_REFUSED') || 
          (error.request && error.request.status === 0)) {
        errorMessage += '\n\n⚠️ Backend server is not running!\n\n';
        errorMessage += 'Please start the backend server:\n';
        errorMessage += '1. Open a terminal in: face-similarity-app/python-backend\n';
        errorMessage += '2. Activate virtual environment: .venv\\Scripts\\activate (Windows)\n';
        errorMessage += '3. Run: python app_v2.py\n\n';
        errorMessage += 'Or run both servers together from project root: npm run dev';
      } else if (error.response) {
        errorMessage += `Server error: ${error.response.status}`;
        if (error.response.data && error.response.data.error) {
          errorMessage += ` - ${error.response.data.error}`;
        }
      } else if (error.request) {
        errorMessage += 'Cannot connect to server. Make sure the backend is running on port 5001.';
      } else {
        errorMessage += error.message;
      }
      
      alert(errorMessage);
    }
  };

  const addCriminal = async (formData) => {
    try {
      await apiService.addCriminal(formData);
      alert('Criminal profile added successfully!');
      setShowAddForm(false);
      loadCriminals();
    } catch (error) {
      console.error('Error adding criminal:', error);
      alert('Failed to add criminal profile. Check console for details.');
    }
  };

  const deleteCriminal = async (criminalId) => {
    try {
      if (window.confirm('Are you sure you want to delete this criminal?')) {
        await apiService.deleteCriminal(criminalId);
        alert('Criminal deleted successfully!');
        loadCriminals();
      }
    } catch (error) {
      console.error('Error deleting criminal:', error);
      alert('Failed to delete criminal. Check console for details.');
    }
  };

  useEffect(() => {
    loadCriminals();
  }, []);

  return (
    <PageContainer variant="default">
      <div className="tab-content">
        <div className="database-header">
          <h2 className="section-title">Criminal Database Management</h2>
          <button 
            className="add-new-button"
            onClick={() => setShowAddForm(true)}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" style={{width: '20px', height: '20px'}}>
              <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/>
            </svg>
            Add New Criminal
          </button>
        </div>

        <CriminalList
          criminals={criminals}
          onDelete={deleteCriminal}
          onRefresh={loadCriminals}
        />

        {showAddForm && (
          <AddCriminalForm
            onSubmit={addCriminal}
            onCancel={() => setShowAddForm(false)}
          />
        )}
      </div>
    </PageContainer>
  );
};

export default DatabasePage;
