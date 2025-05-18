# Actuamind UI

This is the React-based frontend for the Actuamind Enterprise AI Knowledge Platform. It provides a modern, responsive user interface for interacting with code repositories through natural language.

## Features

- Repository management (add, select, view status)
- Natural language chat interface for code queries
- Repository ingestion status tracking
- Responsive design with Tailwind CSS
- Markdown and code syntax highlighting

## Technologies Used

- React 18
- TypeScript
- Tailwind CSS
- React Router
- Axios for API communication
- React Markdown for rendering markdown content
- React Syntax Highlighter for code blocks

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

1. Clone the repository
2. Navigate to the UI directory:
   ```
   cd actuamind/ui
   ```
3. Install dependencies:
   ```
   npm install
   ```
4. Create a `.env` file in the root directory with the following content:
   ```
   REACT_APP_BACKEND_API_URL=http://localhost:8000
   ```
   Adjust the URL if your backend is running on a different host/port.

### Development

Start the development server:

```
npm start
```

This will run the app in development mode. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Building for Production

```
npm run build
```

This builds the app for production to the `build` folder.

## Project Structure

```
src/
├── components/        # Reusable UI components
│   ├── chat/          # Chat-related components
│   ├── layout/        # Layout components (Header, Sidebar, etc.)
│   ├── repository/    # Repository management components
│   └── ui/            # Generic UI components
├── context/           # React context providers
├── hooks/             # Custom React hooks
├── pages/             # Page components
├── services/          # API service functions
├── types/             # TypeScript type definitions
└── utils/             # Utility functions
```

## Backend Integration

This UI is designed to work with the Actuamind backend API. Make sure the backend server is running before starting the UI.

## License

MIT 