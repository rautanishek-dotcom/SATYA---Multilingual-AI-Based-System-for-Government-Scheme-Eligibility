import React, { useState } from 'react';
import { PlusCircle, Database, Users } from 'lucide-react';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('schemes');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_beneficiaries: '',
    official_website: '',
    application_process: ''
  });
  const [status, setStatus] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAddScheme = async (e) => {
    e.preventDefault();
    setStatus('Loading...');
    try {
      const response = await fetch('http://localhost:5000/api/schemes/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (response.ok) {
        setStatus('Scheme added successfully!');
        setFormData({ name: '', description: '', target_beneficiaries: '', official_website: '', application_process: '' });
      } else {
        setStatus('Failed to add scheme.');
      }
    } catch (err) {
      setStatus('Error connecting to server.');
    }
  };

  return (
    <div className="container animate-fade-in" style={styles.container}>
      <h2 style={styles.title}>Admin Panel</h2>

      <div style={styles.tabContainer}>
        <button 
          className={activeTab === 'schemes' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => setActiveTab('schemes')}
          style={styles.tabBtn}
        >
          <Database size={18} /> Manage Schemes
        </button>
        <button 
          className={activeTab === 'users' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => setActiveTab('users')}
          style={styles.tabBtn}
        >
          <Users size={18} /> Manage Users
        </button>
      </div>

      {activeTab === 'schemes' && (
        <div className="glass-card" style={styles.card}>
          <h3 style={styles.cardTitle}><PlusCircle size={20} color="var(--primary-color)" /> Add New Scheme</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>Populate the database with a new welfare program.</p>
          
          {status && <div style={{ marginBottom: '15px', color: status.includes('success') ? 'var(--secondary-color)' : 'var(--error-color)' }}>{status}</div>}
          
          <form onSubmit={handleAddScheme} style={styles.form}>
            <div style={styles.inputGroup}>
              <label>Scheme Name</label>
              <input type="text" name="name" value={formData.name} onChange={handleChange} required style={styles.input} />
            </div>

            <div style={styles.inputGroup}>
              <label>Description</label>
              <textarea name="description" value={formData.description} onChange={handleChange} required style={{ ...styles.input, minHeight: '100px' }}></textarea>
            </div>

            <div style={styles.row}>
              <div style={styles.inputGroup}>
                <label>Target Beneficiaries</label>
                <input type="text" name="target_beneficiaries" value={formData.target_beneficiaries} onChange={handleChange} required style={styles.input} />
              </div>
              <div style={styles.inputGroup}>
                <label>Official Website URL</label>
                <input type="url" name="official_website" value={formData.official_website} onChange={handleChange} required style={styles.input} />
              </div>
            </div>

            <div style={styles.inputGroup}>
              <label>Application Process</label>
              <textarea name="application_process" value={formData.application_process} onChange={handleChange} required style={{ ...styles.input, minHeight: '80px' }}></textarea>
            </div>

            <button type="submit" className="btn-primary" style={styles.submitBtn}>Save Scheme to Database</button>
          </form>
        </div>
      )}

      {activeTab === 'users' && (
        <div className="glass-card" style={{ ...styles.card, textAlign: 'center', padding: '60px' }}>
          <Users size={40} color="var(--text-muted)" style={{ marginBottom: '20px' }} />
          <h3>User Management</h3>
          <p style={{ color: 'var(--text-muted)' }}>This section is reserved for future implementation of user analytics and management.</p>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '40px 0',
    maxWidth: '800px',
    margin: '0 auto',
  },
  title: {
    fontSize: '2.5rem',
    marginBottom: '30px',
  },
  tabContainer: {
    display: 'flex',
    gap: '15px',
    marginBottom: '30px',
  },
  tabBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
  },
  card: {
    padding: '30px',
  },
  cardTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '1.5rem',
    marginBottom: '10px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    flex: 1,
  },
  row: {
    display: 'flex',
    gap: '15px',
  },
  input: {
    padding: '12px 15px',
    fontSize: '1rem',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--border-radius)',
    color: 'var(--text-light)',
    outline: 'none',
  },
  submitBtn: {
    padding: '15px',
    fontSize: '1.1rem',
    marginTop: '10px',
  }
};

export default AdminDashboard;
