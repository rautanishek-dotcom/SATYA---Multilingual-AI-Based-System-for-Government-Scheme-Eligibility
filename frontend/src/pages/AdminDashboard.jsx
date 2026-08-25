import React, { useState, useEffect } from 'react';
import { PlusCircle, Database, Users, Trash2, Shield, Calendar, Mail } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const AdminDashboard = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('schemes');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_beneficiaries: '',
    official_website: '',
    application_process: '',
    state: 'All India'
  });
  
  const [status, setStatus] = useState('');
  const [stats, setStats] = useState({ total_users: 0, total_schemes: 0 });
  const [usersList, setUsersList] = useState([]);
  const [schemesList, setSchemesList] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'schemes') fetchSchemes();
  }, [activeTab]);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch('http://localhost:5000/api/admin/dashboard-stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (response.ok) setStats(data);
    } catch {
      console.error("Failed to fetch stats");
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch('http://localhost:5000/api/admin/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (response.ok) setUsersList(data);
    } catch {
      console.error("Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  const fetchSchemes = async () => {
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch('http://localhost:5000/api/admin/all-schemes', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (response.ok) setSchemesList(data);
    } catch {
      console.error("Failed to fetch schemes");
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAddScheme = async (e) => {
    e.preventDefault();
    setStatus(t('Loading', 'Loading...'));
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch('http://localhost:5000/api/admin/add-scheme', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      if (response.ok) {
        setStatus(t('SchemeAddedSuccess', 'Scheme added successfully!'));
        setFormData({ name: '', description: '', target_beneficiaries: '', official_website: '', application_process: '', state: 'All India' });
        fetchStats();
        fetchSchemes();
      } else {
        const data = await response.json();
        setStatus(data.error || t('SchemeAddedFailed', 'Failed to add scheme.'));
      }
    } catch {
      setStatus(t('ErrorConnecting', 'Error connecting to server.'));
    }
  };

  const handleDeleteScheme = async (schemeId) => {
    if (!window.confirm(t('ConfirmDeleteScheme', 'Are you sure you want to delete this scheme?'))) return;
    
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch(`http://localhost:5000/api/admin/delete-scheme/${schemeId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        setSchemesList(schemesList.filter(s => s._id !== schemeId));
        fetchStats();
      } else {
        const data = await response.json();
        alert(data.error || t('ErrorDeletingScheme', "Error deleting scheme"));
      }
    } catch {
      alert(t('ErrorDeletingScheme', "Error deleting scheme"));
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm(t('ConfirmDeleteUser', 'Are you sure you want to delete this user? This action is irreversible.'))) return;
    
    try {
      const token = localStorage.getItem('satya_token');
      const response = await fetch(`http://localhost:5000/api/admin/delete-user/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      if (response.ok) {
        setUsersList(usersList.filter(u => u._id !== userId));
        fetchStats();
      } else {
        alert(data.error || t('FailedToDeleteUser', "Failed to delete user"));
      }
    } catch {
      alert(t('ErrorDeletingUser', "Error deleting user"));
    }
  };

  return (
    <div className="container animate-fade-in" style={styles.container}>
      <h2 style={styles.title}>{t('AdminPanel', 'Admin Panel')}</h2>

      <div style={styles.tabContainer}>
        <button 
          className={activeTab === 'schemes' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => setActiveTab('schemes')}
          style={styles.tabBtn}
        >
          <Database size={18} /> {t('ManageSchemes', 'Manage Schemes')} ({stats.total_schemes})
        </button>
        <button 
          className={activeTab === 'users' ? 'btn-primary' : 'btn-secondary'} 
          onClick={() => setActiveTab('users')}
          style={styles.tabBtn}
        >
          <Users size={18} /> {t('ManageUsers', 'Manage Users')} ({stats.total_users})
        </button>
      </div>

      {activeTab === 'schemes' && (
        <>
          <div className="glass-card" style={styles.card}>
            <h3 style={styles.cardTitle}><PlusCircle size={20} color="var(--primary-color)" /> {t('AddNewScheme', 'Add New Scheme')}</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>{t('PopulateDatabaseDesc', 'Populate the database with a new welfare program.')}</p>
            
            {status && <div style={{ marginBottom: '15px', color: status.includes('success') || status.includes('यशस्वी') ? 'var(--secondary-color)' : 'var(--error-color)' }}>{status}</div>}
            
            <form onSubmit={handleAddScheme} style={styles.form}>
              <div style={styles.inputGroup}>
                <label>{t('SchemeName', 'Scheme Name')}</label>
                <input type="text" name="name" value={formData.name} onChange={handleChange} required style={styles.input} />
              </div>

              <div style={styles.inputGroup}>
                <label>{t('Description', 'Description')}</label>
                <textarea name="description" value={formData.description} onChange={handleChange} required style={{ ...styles.input, minHeight: '100px' }}></textarea>
              </div>

              <div style={styles.row}>
                <div style={styles.inputGroup}>
                  <label>{t('TargetBeneficiaries', 'Target Beneficiaries')}</label>
                  <input type="text" name="target_beneficiaries" value={formData.target_beneficiaries} onChange={handleChange} required style={styles.input} />
                </div>
                <div style={styles.inputGroup}>
                  <label>{t('OfficialWebsiteURL', 'Official Website URL')}</label>
                  <input type="url" name="official_website" value={formData.official_website} onChange={handleChange} required style={styles.input} />
                </div>
              </div>

              <div style={styles.inputGroup}>
                <label>{t('ApplicationProcess', 'Application Process')}</label>
                <textarea name="application_process" value={formData.application_process} onChange={handleChange} required style={{ ...styles.input, minHeight: '80px' }}></textarea>
              </div>

              <div style={styles.inputGroup}>
                <label>{t('State', 'State')}</label>
                <select name="state" value={formData.state} onChange={handleChange} style={styles.input}>
                  <option value="All India">{t('AllIndia')} ({t('Central')})</option>
                  <option value="Maharashtra">{t('Maharashtra')}</option>
                  <option value="Tamil Nadu">{t('TamilNadu')}</option>
                  <option value="Karnataka">{t('Karnataka')}</option>
                  <option value="Gujarat">{t('Gujarat')}</option>
                  <option value="Uttar Pradesh">{t('UttarPradesh')}</option>
                  <option value="West Bengal">{t('WestBengal')}</option>
                  <option value="Kerala">{t('Kerala')}</option>
                  <option value="Punjab">{t('Punjab')}</option>
                  <option value="Rajasthan">{t('Rajasthan')}</option>
                </select>
              </div>

              <button type="submit" className="btn-primary" style={styles.submitBtn}>{t('SaveSchemeBtn', 'Save Scheme to Database')}</button>
            </form>
          </div>

          <div style={{ marginTop: '40px' }}>
            <h3 style={{ marginBottom: '20px' }}>{t('ExistingSchemes', 'Existing Schemes')}</h3>
            <div style={styles.listContainer}>
              {schemesList.map((scheme) => (
                <div key={scheme._id} className="glass-card" style={styles.listItem}>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: 0 }}>{scheme.name}</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '5px 0' }}>{scheme.category} • {scheme.state}</p>
                  </div>
                  <button 
                    onClick={() => handleDeleteScheme(scheme._id)}
                    style={styles.deleteBtn}
                    title={t('DeleteScheme', 'Delete Scheme')}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'users' && (
        <div className="glass-card" style={styles.card}>
          <h3 style={styles.cardTitle}><Users size={20} color="var(--primary-color)" /> {t('UserManagement', 'User Management')}</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '30px' }}>{t('UserManagementDescDetail', 'List of registered citizens and administrators.')}</p>
          
          {loading ? (
            <p>{t('LoadingUsers', 'Loading users...')}</p>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr style={styles.tr}>
                    <th style={styles.th}>{t('Name')}</th>
                    <th style={styles.th}>{t('Email')}</th>
                    <th style={styles.th}>{t('Role')}</th>
                    <th style={styles.th}>{t('Joined')}</th>
                    <th style={styles.th}>{t('Action')}</th>
                  </tr>
                </thead>
                <tbody>
                  {usersList.map((user) => (
                    <tr key={user._id} style={styles.tr}>
                      <td style={styles.td}><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Shield size={14} color={user.role === 'admin' ? 'var(--primary-color)' : 'var(--text-muted)'} /> {user.name}</div></td>
                      <td style={styles.td}><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Mail size={14} color="var(--text-muted)" /> {user.email}</div></td>
                      <td style={styles.td}><span style={{ ...styles.badge, background: user.role === 'admin' ? 'rgba(79, 70, 229, 0.2)' : 'rgba(255, 255, 255, 0.05)' }}>{user.role}</span></td>
                      <td style={styles.td}><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Calendar size={14} color="var(--text-muted)" /> {new Date(user.created_at).toLocaleDateString()}</div></td>
                      <td style={styles.td}>
                        <button 
                          onClick={() => handleDeleteUser(user._id)}
                          style={styles.deleteBtn}
                          title={t('DeleteUser', 'Delete User')}
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '40px 0',
    maxWidth: '900px',
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
    marginBottom: '30px',
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
  },
  listContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '15px',
  },
  listItem: {
    padding: '15px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    border: '1px solid var(--border-color)',
  },
  deleteBtn: {
    background: 'rgba(239, 68, 68, 0.1)',
    color: '#ef4444',
    border: 'none',
    padding: '8px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
  },
  th: {
    padding: '12px 15px',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-muted)',
    fontSize: '0.9rem',
    fontWeight: 500,
  },
  td: {
    padding: '15px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    fontSize: '0.95rem',
  },
  tr: {
    transition: 'background 0.2s ease',
  },
  badge: {
    padding: '4px 10px',
    borderRadius: '20px',
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontWeight: 600,
  }
};

export default AdminDashboard;
