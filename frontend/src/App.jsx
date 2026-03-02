import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function App() {
  const [bib, setBib] = useState('')
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)
  
  // State for the full-screen modal
  const [selectedImage, setSelectedImage] = useState(null)
  
  // Reference to trigger the hidden file input
  const fileInputRef = useRef(null)

  // Load all photos as soon as the website opens
  useEffect(() => {
    fetchAllPhotos()
  }, [])

  const fetchAllPhotos = async () => {
    setLoading(true)
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/photos/all')
      setPhotos(response.data.photos)
    } catch (error) {
      console.error("Error fetching gallery:", error)
    }
    setLoading(false)
  }

  const handleBibSearch = async (e) => {
    e.preventDefault()
    if (!bib.trim()) {
        fetchAllPhotos()
        return
    }
    setLoading(true)
    try {
      const response = await axios.get(`http://127.0.0.1:8000/api/search/${bib.trim()}`)
      setPhotos(response.data.found_photos)
    } catch (error) {
      alert("Search failed. Check if Backend is running.")
    }
    setLoading(false)
  }

  // --- NEW: FACE SEARCH LOGIC ---
  const handleFaceSearch = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    setLoading(true)
    
    // We must use FormData to send a physical file to FastAPI
    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await axios.post('http://127.0.0.1:8000/api/search-face/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.data.error) {
        alert(response.data.error)
      } else {
        setPhotos(response.data.found_photos)
        setBib('') // Clear bib text since we used face search
      }
    } catch (error) {
      alert("Face search failed. Check if Backend is running and weights are downloaded.")
      console.error(error)
    }
    
    // Reset the input so the user can select the same file again if needed
    event.target.value = null
    setLoading(false)
  }

  const handleShowGallery = () => {
    setBib('')
    fetchAllPhotos()
  }

  // --- NEW: DOWNLOAD LOGIC ---
  const handleDownload = async (url) => {
    try {
      // Extract the filename from the URL (e.g., "http://.../images/photo1.jpg" -> "photo1.jpg")
      const filename = url.substring(url.lastIndexOf('/') + 1)
      
      const response = await axios.get(`http://127.0.0.1:8000/api/download/${filename}`, {
        responseType: 'blob', // Important for downloading files
      })
      
      // Create a temporary hidden link to trigger the browser download
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', `PhotoEase_${filename}`)
      document.body.appendChild(link)
      link.click()
      link.parentNode.removeChild(link)
      
    } catch (error) {
      alert("Download failed.")
      console.error(error)
    }
  }

  return (
    <div style={styles.fullScreenWrapper}>
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>🏃‍♂️ PhotoEase</h1>
          <p style={styles.subtitle}>Relive your marathon moments instantly.</p>
        </header>
        
        <form onSubmit={handleBibSearch} style={styles.searchContainer}>
          <input 
            type="text" 
            placeholder="Search Bib (e.g. M90006)" 
            value={bib}
            onChange={(e) => setBib(e.target.value.toUpperCase())}
            style={styles.input}
          />
          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? '...' : 'Bib Search'}
          </button>
          
          <div style={styles.divider}></div>

          {/* NEW: Hidden file input and visible Face Search Button */}
          <input 
            type="file" 
            accept="image/*" 
            ref={fileInputRef} 
            onChange={handleFaceSearch} 
            style={{ display: 'none' }} 
          />
          <button 
            type="button" 
            onClick={() => fileInputRef.current.click()} 
            style={styles.faceButton}
            disabled={loading}
          >
            {loading ? '...' : 'Face Search'}
          </button>

          <button type="button" onClick={handleShowGallery} style={styles.galleryButton}>
            Gallery
          </button>
        </form>

        {/* --- NEW CONDITIONAL RENDERING FOR LOADING & GALLERY --- */}
        {loading ? (
          <div style={styles.spinnerContainer}>
            {/* Self-contained SVG Loading Circle */}
            <svg width="60" height="60" viewBox="0 0 50 50">
              <circle cx="25" cy="25" r="20" fill="none" stroke="#00f2fe" strokeWidth="4" strokeLinecap="round" strokeDasharray="90" strokeDashoffset="40">
                <animateTransform attributeName="transform" type="rotate" repeatCount="indefinite" dur="1s" values="0 25 25;360 25 25"/>
              </circle>
            </svg>
            <p style={styles.spinnerText}>AI is scanning the database...</p>
          </div>
        ) : (
          <>
            {photos.length > 0 ? (
              <div style={styles.grid}>
                {photos.map((url, index) => (
                  <div key={index} style={styles.card}>
                    <img 
                      src={url} 
                      alt="Marathon" 
                      style={styles.image} 
                      onClick={() => setSelectedImage(url)} 
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p style={styles.notFoundText}>No photos found. Try another search!</p>
            )}
          </>
        )}
      </div>

      {/* FULL SCREEN MODAL WITH DOWNLOAD BUTTON */}
      {selectedImage && (
        <div style={styles.modalOverlay} onClick={() => setSelectedImage(null)}>
          <button style={styles.closeButton} onClick={() => setSelectedImage(null)}>✕</button>
          
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <img src={selectedImage} alt="Full Screen" style={styles.fullScreenImage} />
            <button style={styles.downloadButton} onClick={() => handleDownload(selectedImage)}>
              ⬇️ Download Photo
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const styles = {
  fullScreenWrapper: { width: '100vw', minHeight: '100vh', backgroundColor: '#0f0f12', color: '#fff', fontFamily: "'Poppins', sans-serif", display: 'flex', justifyContent: 'center' },
  container: { width: '100%', maxWidth: '1200px', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '60px 20px' },
  header: { textAlign: 'center', marginBottom: '30px' },
  title: { fontSize: '3.5rem', fontWeight: '900', margin: '0', background: 'linear-gradient(90deg, #4facfe, #00f2fe)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', marginTop: '10px' },
  searchContainer: { display: 'flex', alignItems: 'center', backgroundColor: '#1a1a1e', padding: '8px', borderRadius: '50px', border: '1px solid #333', marginBottom: '60px', width: 'fit-content', gap: '10px' },
  input: { padding: '12px 20px', width: '220px', border: 'none', backgroundColor: 'transparent', color: '#fff', outline: 'none' },
  button: { padding: '12px 25px', borderRadius: '40px', border: 'none', background: 'linear-gradient(135deg, #007bff, #00c6ff)', color: '#fff', fontWeight: '700', cursor: 'pointer' },
  
  divider: { height: '30px', width: '1px', backgroundColor: '#444', margin: '0 5px' },
  
  faceButton: { padding: '12px 20px', borderRadius: '40px', border: '1px solid #00f2fe', backgroundColor: 'rgba(0, 242, 254, 0.1)', color: '#00f2fe', fontWeight: '600', cursor: 'pointer', transition: '0.3s' },
  galleryButton: { padding: '12px 25px', borderRadius: '40px', border: '1px solid #444', backgroundColor: '#2a2a2e', color: '#ccc', fontWeight: '600', cursor: 'pointer' },
  
  // --- NEW STYLES FOR LOADING & EMPTY STATES ---
  spinnerContainer: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', marginTop: '60px' },
  spinnerText: { color: '#00f2fe', marginTop: '20px', fontSize: '1.2rem', fontWeight: '500' },
  notFoundText: { color: '#888', marginTop: '60px', fontSize: '1.2rem', textAlign: 'center' },
  // ---------------------------------------------

  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '20px', width: '100%' },
  card: { borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 15px rgba(0,0,0,0.3)', transition: 'transform 0.2s' },
  image: { width: '100%', height: '220px', objectFit: 'cover', display: 'block', cursor: 'pointer' },
  
  modalOverlay: { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.9)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 },
  closeButton: { position: 'absolute', top: '30px', right: '40px', background: 'none', border: 'none', color: '#fff', fontSize: '2rem', cursor: 'pointer', zIndex: 1001 },
  modalContent: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', maxWidth: '90%', maxHeight: '90%' },
  fullScreenImage: { maxWidth: '100%', maxHeight: '75vh', objectFit: 'contain', borderRadius: '8px', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' },
  downloadButton: { padding: '12px 30px', borderRadius: '30px', border: 'none', backgroundColor: '#4facfe', color: '#fff', fontSize: '1.1rem', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 15px rgba(79, 172, 254, 0.4)' }
}

export default App