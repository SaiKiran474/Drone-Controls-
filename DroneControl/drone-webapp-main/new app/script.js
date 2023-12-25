// var speedometer1 = new speedometer();
// document.getElementById('meter1').append(speedometer1.elm);

// var speedoMeterDefault = new speedometer();
//     document.getElementById('speedometer-default').append(speedoMeterDefault.elm);

var helper = document.querySelector("#example1");
var gauge1 = new FlexGauge({
    appendTo: helper, // Use the correct ID of the container element
    animateEasing: true,
  //   elementId: 'example1_canvas', // Use the correct ID of the canvas element
    elementWidth: 150,
    elementHeight: 150,
    arcSize: 65,
    arcAngleStart: 1,
    arcFillPercent: 0.80,
    arcStrokeFg: 20,
    arcStrokeBg: 10,
    animateSpeed: 1,
    styleArcFg: 'btn-danger',
    styleSrc: 'background-color'
});


$(document).ready(function () {
    // Create and attach the first FlexGauge instance
    var gauge1 = new FlexGauge({
      appendTo: helper, // Use the correct ID of the container element
      animateEasing: true,
    //   elementId: 'example1_canvas', // Use the correct ID of the canvas element
      elementWidth: 150,
      elementHeight: 150,
      arcSize: 65,
      arcAngleStart: 1,
      arcFillPercent: 0.80,
      arcStrokeFg: 20,
      arcStrokeBg: 10,
      animateSpeed: 1,
      styleArcFg: 'btn-danger',
      styleSrc: 'background-color'
    });
  
    // Create and attach the second FlexGauge instance
    var gauge2 = new FlexGauge({
      appendTo: '#example2', // Use the correct ID of the container element
      animateEasing: true,
    //   elementId: 'example2_canvas', // Use the correct ID of the canvas element
      elementWidth: 150,
      elementHeight: 150,
      arcSize: 65,
      arcAngleStart: 1,
      arcFillPercent: 0.80,
      arcStrokeFg: 20,
      arcStrokeBg: 10,
      animateSpeed: 1,
      styleArcFg: 'btn-success',
      styleSrc: 'background-color'
    });
  });
  