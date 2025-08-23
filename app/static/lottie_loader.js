document.addEventListener('DOMContentLoaded', function () {
    function initLottieLoader(loaderId, animId, animPath, duration = 3000, loop = true, speed = 1) {
        var loader = document.getElementById(loaderId);
        var animContainer = document.getElementById(animId);

        if (!loader || !animContainer) return;

        // Load Lottie Animation
        var animation = lottie.loadAnimation({
            container: animContainer,
            renderer: 'svg',
            loop: loop,
            autoplay: true,
            path: animPath
        });

        // Set Playback Speed
        animation.setSpeed(speed);

        // Fade Out After Duration
        setTimeout(function () {
            loader.style.transition = "opacity 1s ease-out";
            loader.style.opacity = 0;
            setTimeout(function () {
                loader.style.display = "none";
            }, 1000);
        }, duration);
    }

    // Home Page Loader
    initLottieLoader('lottie-loader', 'lottie-animation', '/static/animations/Hospital.json', 2600);

    // Profile Page Loader
    initLottieLoader('dr-loader', 'dr-loader-animation', '/static/animations/Doctor and health symbols.json', 1600, true, 5);

    // Profile Page Loader
    // initLottieLoader('doctor-loader', 'doctor-loader-animation', '/static/animations/Search Doctor.json', 2000, true, 2);

    // Chat Page Loader with 4x Speed
    initLottieLoader('chat-loader', 'chat-loader-animation', '/static/animations/Chat Doctor.json', 1000, true, 4);
});
