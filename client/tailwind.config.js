/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    light: '#4fd1c5',
                    DEFAULT: '#38b2ac',
                    dark: '#2c7a7b',
                },
                secondary: {
                    light: '#63b3ed',
                    DEFAULT: '#4299e1',
                    dark: '#2b6cb0',
                },
            },
        },
    },
    plugins: [],
}
