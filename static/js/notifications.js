document.addEventListener('DOMContentLoaded', () => {
    const messages = document.querySelectorAll('.message');

    messages.forEach(msg => {
        // Setup close button
        const closeBtn = msg.querySelector('.message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                dismissMessage(msg);
            });
        }

        // Auto dismiss after 5 seconds
        // Store timeout ID so we could potentially clear it on hover if we wanted
        const timerId = setTimeout(() => {
            dismissMessage(msg);
        }, 5000);
    });

    function dismissMessage(element) {
        if (element.classList.contains('sliding-out')) return;

        element.classList.add('sliding-out');

        // Listen for animation end to remove from DOM
        element.addEventListener('animationend', () => {
            element.remove();

            // Check if messages container is empty and remove it if necessary
            // (Optional, but keeps DOM clean)
            const container = document.querySelector('.messages');
            if (container && container.children.length === 0) {
                // container.remove(); // Maybe keeping it is fine
            }
        });
    }
});
