import { FC } from 'react';

export const RogLogoRainbowWave: FC = () => {
  return (
    <svg width="512" height="384" viewBox="0 0 512 384" version="1.1" id="svg8">
      <defs id="defs8" />
      <linearGradient
        id="A"
        x1="23.363337"
        y1="0"
        x2="0"
        y2="0"
        gradientTransform="matrix(21.117032,0,0,11.256481,9.3178305,7.278782)"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0%">
          <animate
            attributeName="stop-color"
            values="red;orange;yellow;green;blue;indigo;violet;red"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="16%">
          <animate
            attributeName="stop-color"
            values="orange;yellow;green;blue;indigo;violet;red;orange"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="33%">
          <animate
            attributeName="stop-color"
            values="yellow;green;blue;indigo;violet;red;orange;yellow"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="49%">
          <animate
            attributeName="stop-color"
            values="green;blue;indigo;violet;red;orange;yellow;green"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="66%">
          <animate
            attributeName="stop-color"
            values="blue;indigo;violet;red;orange;yellow;green;blue"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="83%">
          <animate
            attributeName="stop-color"
            values="indigo;violet;red;orange;yellow;green;blue;indigo"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
        <stop offset="100%">
          <animate
            attributeName="stop-color"
            values="violet;red;orange;yellow;green;blue;indigo;violet"
            dur="5s"
            repeatCount="indefinite"
          />
        </stop>
      </linearGradient>
      <path
        d="m 379.34108,139.71627 c -77.08817,37.1565 -207.82972,129.66232 -207.82972,129.66232 a 484.88463,484.88463 0 0 0 79.86335,32.68538 c 46.25291,14.03005 89.26811,21.43052 111.31533,16.49687 49.79896,-11.1007 103.144,-118.40744 120.41172,-165.89375 l -96.66857,41.62761 c -20.19709,9.25058 -96.82274,46.25291 -96.82274,46.25291 l 120.56591,-36.23144 c -2.15847,4.93364 -33.9188,76.31729 -74.46718,84.33446 C 295.1608,296.6678 218.8435,267.22011 218.8435,267.22011 A 1383.5631,1383.5631 0 0 1 487.26454,130.61986 38.389911,38.389911 0 0 0 502.68217,105.33494 379.11965,379.11965 0 0 0 379.34108,139.71627 Z M 155.6312,274.31223 c -5.08782,-8.94223 1.2334,-21.27634 40.70255,-50.2615 C 231.79432,197.99493 359.91486,90.84237 482.33092,62.31974 A 370.02324,370.02324 0 0 0 326.61277,80.20419 c -32.68538,10.17564 -80.94258,55.81184 -169.59399,141.68808 -11.87157,6.62958 -54.7326,-18.19281 -79.40082,-30.83527 0,0 40.85673,65.06242 55.19514,84.48864 a 174.99016,174.99016 0 0 0 61.67054,47.94885 333.7918,333.7918 0 0 1 -38.85244,-49.18226 z M 9.3178305,175.79354 c 0,0 19.8887485,53.03666 32.9937365,61.67054 a 233.73135,233.73135 0 0 0 69.533543,27.44339 L 62.046145,223.12568 Z"
        fill="url(#A)"
        id="path8"
      />
    </svg>
  );
};
