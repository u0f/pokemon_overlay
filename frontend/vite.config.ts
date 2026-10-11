import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// OBS 24 embeds Chromium 75; newer OBS versions accept the same bundle.
export default defineConfig({plugins:[react()],base:'/',build:{target:'chrome75',cssTarget:'chrome75',assetsDir:'static'},server:{proxy:{'/api':'http://127.0.0.1:8765','/assets':'http://127.0.0.1:8765','/ws':{target:'ws://127.0.0.1:8765',ws:true}}}});
