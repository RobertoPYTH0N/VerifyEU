# Media Provenance Frontend

A React-based web interface for the Media Provenance System. This frontend provides an intuitive UI for registering media and checking their provenance.

## Features

- **Two Main Workflows:**
  - **Register Media**: Login required. Upload images to register them in the database with cryptographic signatures
  - **Check Provenance**: No login required. Upload an image to search for similar media in the database

- **Authentication:**
  - User registration with password validation (minimum 8 characters)
  - Secure login with bcrypt password hashing
  - Session management with logout

- **File Management:**
  - Drag-and-drop file upload
  - File type validation (JPG, PNG, GIF, BMP, WEBP, TIFF)
  - File preview before upload
  - Maximum file size: 50MB

- **Results Display:**
  - Confidence tiers (EXACT MATCH, VERY SIMILAR, SIMILAR, POSSIBLY RELATED)
  - Similarity scores
  - Perceptual hash distances (pHash, dHash, aHash)
  - SHA-256 hash information
  - Expandable match details for all results

## Setup

### Prerequisites

- Node.js 14+ and npm

### Installation

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Ensure the Flask backend is running:**
   ```bash
   # In the parent directory
   python api.py
   ```
   The API should be accessible at `http://localhost:5000`

3. **Start the development server:**
   ```bash
   npm start
   ```

   The frontend will automatically open at `http://localhost:3000`

## Usage

### Register Media

1. Click the "Register Media" button
2. If not logged in, you'll see the login screen:
   - **New users**: Click "Don't have an account? Register" and fill in a username and password (min 8 chars)
   - **Existing users**: Enter your credentials and click "Login"
3. Select an image file (drag-and-drop or click to browse)
4. Click "Register Media" to upload
5. View the confirmation with asset ID and SHA-256 hash

### Check Provenance

1. Click the "Check Provenance" button (no login required)
2. Select an image file (drag-and-drop or click to browse)
3. Click "Check Provenance" to search
4. View results:
   - **Top Match**: The most similar image in the database with confidence tier
   - **All Matches**: List of all similar images (up to top 20)
   - Click on any match to expand and see details

## API Endpoints

The frontend communicates with these backend endpoints:

- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/logout` - End user session
- `GET /api/status` - Check authentication status
- `POST /api/media/register` - Register a new image (requires auth)
- `POST /api/media/check` - Check image provenance (no auth required)

## File Structure

```
frontend/
├── public/
│   └── index.html           # HTML entry point
├── src/
│   ├── App.js              # Main app component
│   ├── App.css             # App styles
│   ├── index.js            # React entry point
│   ├── index.css           # Global styles
│   └── components/
│       ├── Header.js       # Header with auth status
│       ├── LoginModal.js   # Login/register modal
│       ├── FileUploader.js # File upload component
│       ├── ResultsDisplay.js # Results display component
│       └── *.css           # Component styles
├── package.json            # Dependencies
└── .gitignore             # Git ignore rules
```

## Development

### Build for Production

```bash
npm run build
```

Creates an optimized production build in the `build/` directory.

### Testing

```bash
npm test
```

Runs the test suite.

## Error Handling

The frontend displays user-friendly error messages for:
- Authentication failures
- Invalid file types or sizes
- API connection errors
- Database errors

## Styling

- **Colors**: Purple/pink gradient theme (`#667eea` to `#764ba2`)
- **Responsive**: Mobile-first design, adaptive to all screen sizes
- **Components**: Smooth transitions and hover effects for better UX

## Notes

- The frontend uses `http://localhost:5000` for API calls. Update this in the API fetch URLs if your backend runs on a different address.
- CORS must be enabled on the backend (it is in `api.py`)
- Authentication state is managed locally; consider adding JWT tokens for production
- File uploads are limited to 50MB on the backend
