import React, { useState, useEffect } from 'react';
import './App.css';
import LoginModal from './components/LoginModal';
import FileUploader from './components/FileUploader';
import ResultsDisplay from './components/ResultsDisplay';
import Header from './components/Header';

function App() {
  const [currentView, setCurrentView] = useState('home'); // home, register-login, register-upload, check-provenance
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [registrationResults, setRegistrationResults] = useState([]);

  // Check auth status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/status');
      const data = await response.json();
      setUser(data.authenticated ? data.user : null);
    } catch (error) {
      console.error('Error checking auth status:', error);
    }
  };

  const handleRegisterClick = () => {
    setCurrentView('register-login');
  };

  const handleCheckClick = () => {
    setCurrentView('check-provenance');
    setResult(null);
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setRegistrationResults([]);
    setCurrentView('register-upload');
  };



  const handleRegisterMediaSuccess = (registerResult) => {
    setRegistrationResults([...registrationResults, registerResult]);
  };

  const handleCheckProvenanceSuccess = (checkResult) => {
    setResult({
      type: 'check',
      data: checkResult.data,
      message: checkResult.message,
      queryImageBase64: checkResult.queryImageBase64,
    });
  };

  return (
    <div className="App">
      <Header />

      {currentView === 'home' && (
        <div className="home-container">
          <div className="hero">
            <h1>VerifyEU</h1>
            <p>Verify the authenticity of digital media with cryptographic hashing and digital signatures</p>
          </div>

          <div className="buttons-container">
            <button
              className="main-button register-button"
              onClick={handleRegisterClick}
            >
              <div className="button-text">
                <h2>Register Media</h2>
                <p>Upload and certify images</p>
              </div>
            </button>

            <button
              className="main-button check-button"
              onClick={handleCheckClick}
            >
              <div className="button-text">
                <h2>Check Provenance</h2>
                <p>Verify an image's authenticity</p>
              </div>
            </button>
          </div>
        </div>
      )}

      {currentView === 'register-login' && (
        <LoginModal
          onSuccess={handleLoginSuccess}
          onCancel={() => setCurrentView('home')}
          isRegistering={true}
        />
      )}

      {currentView === 'register-upload' && (
        <div className="upload-container">
          <button className="back-button" onClick={() => {
            setCurrentView('home');
            setRegistrationResults([]);
            setUser(null);
          }}>
            Back
          </button>
          <div className="upload-card">
            <h2>Register Media</h2>
            <FileUploader
              type="register"
              onSuccess={handleRegisterMediaSuccess}
              user={user}
              registrationResults={registrationResults}
              onAllComplete={() => {
                setCurrentView('home');
                setRegistrationResults([]);
                setUser(null);
              }}
            />
          </div>
        </div>
      )}

      {currentView === 'check-provenance' && (
        <div className="upload-container">
          <button className="back-button" onClick={() => {
            setCurrentView('home');
            setResult(null);
          }}>← Back</button>
          <div className="upload-card">
            <h2>Check Provenance</h2>
            <p className="subtitle">Verify if an image exists in our database</p>
            {!result ? (
              <FileUploader
                type="check"
                onSuccess={handleCheckProvenanceSuccess}
              />
            ) : (
              <ResultsDisplay
                result={result}
                onContinue={() => {
                  setResult(null);
                  setCurrentView('home');
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
