import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [bib, setBib] = useState('')
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)

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

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!bib.trim()) {
        fetchAllPhotos(); // If search is empty, show everything again
        return;
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

  // NEW: Function to handle the Gallery button click
  const handleShowGallery = () => {
    setBib('');       // Clears the text in the search bar
    fetchAllPhotos(); // Fetches all original photos
  }

  return (
    <div style={styles.fullScreenWrapper}>
      <div style={styles.container}>
        <header style={styles.header}>
          <h1 style={styles.title}>🏃‍♂️ PhotoEase</h1>
          <p style={styles.subtitle}>Relive your marathon moments instantly.</p>
        </header>
        
        <form onSubmit={handleSearch} style={styles.searchContainer}>
          <input 
            type="text" 
            placeholder="Search Bib (e.g. M90006)" 
            value={bib}
            onChange={(e) => setBib(e.target.value.toUpperCase())}
            style={styles.input}
          />
          <button type="submit" style={styles.button}>
            {loading ? '...' : 'Search'}
          </button>
          
          {/* NEW: Gallery Button */}
          <button type="button" onClick={handleShowGallery} style={styles.galleryButton}>
            Gallery
          </button>
        </form>

        <div style={styles.grid}>
          {photos.map((url, index) => (
            <div key={index} style={styles.card}>
              <img src={url} alt="Marathon" style={styles.image} />
            </div>
          ))}
        </div>

        {photos.length === 0 && !loading && (
          <p style={{color: '#666', marginTop: '40px'}}>No photos found for that bib number.</p>
        )}
      </div>
    </div>
  )
}

const styles = {
  fullScreenWrapper: {
    width: '100vw',
    minHeight: '100vh',
    backgroundColor: '#0f0f12', 
    color: '#fff', 
    fontFamily: "'Poppins', sans-serif",
    display: 'flex',
    justifyContent: 'center'
  },
  container: { 
    width: '100%',
    maxWidth: '1200px', 
    display: 'flex', 
    flexDirection: 'column', 
    alignItems: 'center',
    padding: '60px 20px' 
  },
  header: { textAlign: 'center', marginBottom: '30px' },
  title: { fontSize: '3.5rem', fontWeight: '900', margin: '0', background: 'linear-gradient(90deg, #4facfe, #00f2fe)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', marginTop: '10px' },
  searchContainer: { 
    display: 'flex', 
    backgroundColor: '#1a1a1e', 
    padding: '8px', 
    borderRadius: '50px', 
    border: '1px solid #333',
    marginBottom: '60px',
    width: 'fit-content',
    gap: '10px' // NEW: Adds a little space between the buttons
  },
  input: { padding: '12px 20px', width: '250px', border: 'none', backgroundColor: 'transparent', color: '#fff', outline: 'none' },
  button: { padding: '12px 30px', borderRadius: '40px', border: 'none', background: 'linear-gradient(135deg, #007bff, #00c6ff)', color: '#fff', fontWeight: '700', cursor: 'pointer' },
  
  // NEW: Styling for the secondary Gallery button
  galleryButton: { 
    padding: '12px 25px', 
    borderRadius: '40px', 
    border: '1px solid #444', 
    backgroundColor: '#2a2a2e', // Darker grey so it doesn't fight the blue search button
    color: '#ccc', 
    fontWeight: '600', 
    cursor: 'pointer' 
  },
  
  grid: { 
    display: 'grid', 
    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', 
    gap: '20px', 
    width: '100%'
  },
  card: { borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 15px rgba(0,0,0,0.3)' },
  image: { 
    width: '100%', 
    height: '220px',    
    objectFit: 'cover', 
    display: 'block' 
  }
}

export default App