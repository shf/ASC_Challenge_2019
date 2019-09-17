var CeleryProgressBar = (function () {
    function onSuccessDefault(progressBarElement, progressBarMessageElement,gifElement, progress) {
        progressBarElement.style.backgroundColor = '#76ce60';
        progressBarElement.style.width = 100 + "%";
        progressBarMessageElement.innerHTML = progress.message;
        gifElement.src='/static/success.gif/';
    }

    function onTerminateDefault(progressBarElement, progressBarMessageElement,gifElement, progress) {
        progressBarElement.style.backgroundColor = '#ffff2e';
        progressBarElement.style.width = 100 + "%";
        progressBarMessageElement.innerHTML = progress.message;
        gifElement.src='/static/terminate.gif/';
    }

    function onErrorDefault(progressBarElement, progressBarMessageElement) {
        progressBarElement.style.backgroundColor = '#dc4f63';
        progressBarMessageElement.innerHTML = progress.message;
        gifElement.src='/static/error.gif/';
    }

    function onProgressDefault(progressBarElement, progressBarMessageElement, progress) {
        progressBarElement.style.backgroundColor = '#68a9ef';
        progressBarElement.style.width = progress.percent*100 + "%";
        progressBarMessageElement.innerHTML = 'Iteration No: ' + progress.iteration + ' <br>' + progress.numOfFilled + ' cells of the total ' + progress.numofCells + ' are filled.' + ' <br>' + 'Current time: ' + progress.fill_time;
    }

    function updateProgress (progressUrl, options) {
        options = options || {};
        var progressBarId = options.progressBarId || 'progress-bar';
        var progressBarMessage = options.progressBarMessageId || 'progress-bar-message';
        var progressBarElement = options.progressBarElement || document.getElementById(progressBarId);
        var progressBarMessageElement = options.progressBarMessageElement || document.getElementById(progressBarMessage);
        var gifElement = document.getElementById('gif');
        var onProgress = options.onProgress || onProgressDefault;
        var onSuccess = options.onSuccess || onSuccessDefault;
        var onTerminate = options.onTerminate || onTerminateDefault;
        var onError = options.onError || onErrorDefault;
        var pollInterval = options.pollInterval || 2000;
        

        fetch(progressUrl).then(function(response) {
            response.json().then(function(data) {
                if (data.state === 'PROGRESS') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                    onProgress(progressBarElement, progressBarMessageElement, data.details);
                }
                if (data.state === 'ERROR') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                    onError(progressBarElement, progressBarMessageElement, gifElement, data.details);
                }
                if (data.state === 'TERMINATE') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                    onTerminate(progressBarElement, progressBarMessageElement, gifElement, data.details);
                } 
                if (data.state === 'SUCCESS') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                    onSuccess(progressBarElement, progressBarMessageElement, gifElement, data.details);
                } 
                
            });
        });
    }
    return {
        onSuccessDefault: onSuccessDefault,
        onErrorDefault: onErrorDefault,
        onProgressDefault: onProgressDefault,
        updateProgress: updateProgress,
        initProgressBar: updateProgress,  // just for api cleanliness
    };
})();