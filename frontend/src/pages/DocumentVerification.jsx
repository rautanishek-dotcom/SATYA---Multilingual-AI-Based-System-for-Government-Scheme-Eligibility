import React from 'react';
import DocumentVerificationComponent from '../components/DocumentVerification';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router-dom';

const DocumentVerificationPage = () => {
    const { t } = useTranslation();
    const storedUser = JSON.parse(localStorage.getItem('satya_user') || '{}');
    const isAadhaarVerified = window.satya_aadhaar_verified === true;

    // Redirect to Aadhaar QR verification if not done in the current application session
    if (!isAadhaarVerified) {
        return <Navigate to="/verify-aadhaar" replace />;
    }

    return (
        <div style={styles.pageWrapper}>
            <div className="container">
                <div style={styles.headerArea}>
                    <h1 className="gradient-text" style={styles.mainTitle}>{t('SecureVerification', 'Secure Identity Verification')}</h1>
                    <p style={styles.mainSubtitle}>{t('VerificationRequired', 'Please verify your official documents to unlock scheme eligibility assessment.')}</p>
                </div>
                
                <div style={styles.componentContainer}>
                    <DocumentVerificationComponent 
                        userId={storedUser.id || storedUser._id} 
                        profileData={window.satya_aadhaar_data} 
                        onVerificationComplete={(success) => {
                            if (success) {
                                console.log("Verification successful!");
                            }
                        }} 
                    />
                </div>
            </div>
        </div>
    );
};

const styles = {
    pageWrapper: {
        minHeight: '100vh',
        padding: '60px 0',
        background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
    },
    headerArea: {
        textAlign: 'center',
        marginBottom: '40px',
    },
    mainTitle: {
        fontSize: '2.5rem',
        fontWeight: 800,
        marginBottom: '15px',
    },
    mainSubtitle: {
        fontSize: '1.1rem',
        color: '#64748b',
        maxWidth: '600px',
        margin: '0 auto',
    },
    componentContainer: {
        maxWidth: '900px',
        margin: '0 auto',
    }
};

export default DocumentVerificationPage;
