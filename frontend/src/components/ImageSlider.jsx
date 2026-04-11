import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const ImageSlider = () => {
  const { t } = useTranslation();
  const images = [
    {
      url: '/slider/1.png',
      title: 'Farmers & Villagers',
      subtitle: 'Supporting the backbone of India',
      key: '1'
    },
    {
      url: '/slider/2.png',
      title: 'Empowering Women',
      subtitle: 'Unlocking opportunities for entrepreneurs',
      key: '2'
    },
    {
      url: '/slider/4.jpg',
      title: 'Strong Leadership',
      subtitle: 'Committed to serving every citizen',
      key: '3'
    },
    {
      url: '/slider/5.jpg',
      title: 'Brighter Future',
      subtitle: 'Investing in our next generation',
      key: '4'
    },
    {
      url: '/slider/6.png',
      title: 'Unity in Diversity',
      subtitle: 'Schemes for every community and region',
      key: '5'
    },
    {
      url: '/slider/7.png',
      title: 'Accessible Governance',
      subtitle: 'Bringing services directly to your doorstep',
      key: '6'
    },
    {
      url: '/slider/8.jpg',
      title: 'Nari Shakti',
      subtitle: 'Empowering women across the nation',
      key: '7'
    },
    {
      url: '/slider/9.png',
      title: 'Village Communities',
      subtitle: 'Building strong communal bonds',
      key: '8'
    },
    {
      url: '/slider/10.png',
      title: 'Local Markets',
      subtitle: 'Boosting rural economy and livelihoods',
      key: '9'
    },
    {
      url: '/slider/11.png',
      title: 'Rural Education',
      subtitle: 'Knowledge for a better tomorrow',
      key: '10'
    }
  ];

  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % images.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [images.length]);

  return (
    <div style={styles.sliderContainer}>
      {images.map((image, index) => (
        <div
          key={index}
          style={{
            ...styles.slide,
            opacity: index === currentIndex ? 1 : 0,
            transform: `scale(${index === currentIndex ? 1 : 1.05})`,
          }}
        >
          {/* Blurred Background Backdrop */}
          <img 
            src={image.url} 
            alt="" 
            style={{...styles.image, filter: 'blur(20px) brightness(0.5)', transform: 'scale(1.2)'}} 
          />
          
          {/* Full Image (Uncropped) */}
          <img 
            src={image.url} 
            alt={image.title} 
            style={{...styles.image, objectFit: 'contain'}} 
          />
          
          <div style={styles.overlay}>
            <div style={styles.content}>
              <h2 style={styles.slideTitle}>{t('Slider' + image.key + 'Title', image.title)}</h2>
              <p style={styles.slideSubtitle}>{t('Slider' + image.key + 'Subtitle', image.subtitle)}</p>
            </div>
          </div>
        </div>
      ))}
      
      <div style={styles.dots}>
        {images.map((_, index) => (
          <div
            key={index}
            onClick={() => setCurrentIndex(index)}
            style={{
              ...styles.dot,
              background: index === currentIndex ? 'var(--primary-color)' : 'rgba(255,255,255,0.3)',
              width: index === currentIndex ? '30px' : '10px',
            }}
          />
        ))}
      </div>
    </div>
  );
};

const styles = {
  sliderContainer: {
    position: 'relative',
    width: '100%',
    height: '450px',
    borderRadius: '24px',
    overflow: 'hidden',
    marginBottom: '60px',
    boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
    border: '1px solid rgba(255,255,255,0.1)',
  },
  slide: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    transition: 'all 1.2s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'flex',
    alignItems: 'flex-end',
  },
  image: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.2) 50%, transparent 100%)',
    padding: '40px',
    paddingTop: '100px',
  },
  content: {
    maxWidth: '600px',
    color: '#fff',
  },
  slideTitle: {
    fontSize: '2.5rem',
    fontWeight: 800,
    marginBottom: '10px',
    textShadow: '0 2px 4px rgba(0,0,0,0.3)',
  },
  slideSubtitle: {
    fontSize: '1.2rem',
    opacity: 0.9,
    fontWeight: 300,
  },
  dots: {
    position: 'absolute',
    bottom: '25px',
    right: '40px',
    display: 'flex',
    gap: '10px',
    zIndex: 10,
  },
  dot: {
    height: '10px',
    borderRadius: '5px',
    cursor: 'pointer',
    transition: 'all 0.4s ease',
  }
};

export default ImageSlider;
